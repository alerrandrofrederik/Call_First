# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze · cache da BrasilAPI
# MAGIC
# MAGIC Consulta `https://brasilapi.com.br/api/cnpj/v1/{cnpj}` só para os CNPJs **válidos** que ainda não estão em
# MAGIC `<catálogo>.<schema>.cnpj_api` (PRD RF-03, D-03) e grava a resposta crua, em append.
# MAGIC
# MAGIC - CNPJs de `crm_leads` e dos arquivos de formulário no Volume `raw` (lidos crus, sem depender do pipeline).
# MAGIC - Resposta 200 ou 4xx é gravada e não é consultada de novo. Timeout ou 5xx não é gravado: o CNPJ é tentado
# MAGIC   na próxima execução, e o job segue (PRD RNF-06).
# MAGIC - Pausa entre chamadas, porque a API pública tem limite de requisições.

# COMMAND ----------

dbutils.widgets.text("catalog", "call_first")
dbutils.widgets.text("schema", "bronze")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

# COMMAND ----------

import json
import os
import sys
import time
from datetime import datetime, timezone

import requests
from pyspark.sql import functions as F

sys.path.append(os.path.abspath("../call_first_etl"))
from utilities.limpeza import cnpj_norm, cnpj_valido  # noqa: E402

alvo = f"{catalog}.{schema}.cnpj_api"
volume = f"/Volumes/{catalog}/{schema}/raw/formularios"

do_crm = spark.table(f"{catalog}.{schema}.crm_leads").select("cnpj")
do_form = spark.read.json(volume).select("cnpj") if os.path.isdir(volume) and os.listdir(volume) else None
todos = do_crm.unionByName(do_form) if do_form is not None else do_crm

candidatos = (todos.select(cnpj_norm(F.col("cnpj")).alias("cnpj"))
              .where(cnpj_valido(F.col("cnpj")))
              .distinct())
if spark.catalog.tableExists(alvo):
    candidatos = candidatos.join(spark.table(alvo).select("cnpj"), "cnpj", "left_anti")
cnpjs = sorted(r.cnpj for r in candidatos.collect())

# COMMAND ----------

linhas, adiados = [], []
for c in cnpjs:
    try:
        r = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{c}", timeout=20)
    except requests.RequestException as e:
        adiados.append({"cnpj": c, "motivo": type(e).__name__})
        continue
    if r.status_code >= 500 or r.status_code == 429:
        adiados.append({"cnpj": c, "motivo": f"HTTP {r.status_code}"})
    else:
        linhas.append((c, r.status_code, r.text, "brasilapi", datetime.now(timezone.utc)))
    time.sleep(0.5)

if linhas:
    (spark.createDataFrame(linhas, "cnpj STRING, status_http INT, resposta STRING, _fonte STRING, _ingerido_em TIMESTAMP")
     .write.mode("append").saveAsTable(alvo))

resultado = {"consultados": len(cnpjs), "gravados": len(linhas), "adiados": adiados,
             "status": {str(s): sum(1 for l in linhas if l[1] == s) for s in sorted({l[1] for l in linhas})}}
print(resultado)
dbutils.notebook.exit(json.dumps(resultado))
