# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze · copiar os formulários do Supabase Storage para o Volume
# MAGIC
# MAGIC Copia do bucket para `/Volumes/<catálogo>/<schema>/raw/formularios/` só os arquivos `.jsonl` que ainda
# MAGIC não estão no Volume (PRD RF-02). Reexecutar não copia nada de novo. O Auto Loader do pipeline
# MAGIC `call_first_etl` lê o Volume em seguida.
# MAGIC
# MAGIC O Storage passa por um Volume porque um endpoint S3 fora da AWS não pode ser external location no
# MAGIC Unity Catalog (PRD D-02). Credenciais: secret scope `call_first`.

# COMMAND ----------

# MAGIC %pip install boto3 -q

# COMMAND ----------

dbutils.widgets.text("catalog", "call_first")
dbutils.widgets.text("schema", "bronze")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

# COMMAND ----------

import json
import os

import boto3
from botocore.config import Config


def segredo(chave):
    return dbutils.secrets.get("call_first", chave)


s3 = boto3.client(
    "s3",
    endpoint_url=segredo("s3_endpoint"),
    region_name=segredo("s3_region"),
    aws_access_key_id=segredo("s3_access_key_id"),
    aws_secret_access_key=segredo("s3_secret_access_key"),
    config=Config(s3={"addressing_style": "path"}),  # o Supabase exige path-style
)
bucket = segredo("s3_bucket")
destino = f"/Volumes/{catalog}/{schema}/raw/formularios"
os.makedirs(destino, exist_ok=True)

copiados, ja_existiam = [], 0
for pagina in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket):
    for obj in pagina.get("Contents", []):
        if not obj["Key"].endswith(".jsonl"):
            continue
        alvo = f"{destino}/{os.path.basename(obj['Key'])}"
        if os.path.exists(alvo):
            ja_existiam += 1
            continue
        s3.download_file(bucket, obj["Key"], alvo)
        copiados.append(os.path.basename(obj["Key"]))

resultado = {"copiados": copiados, "ja_existiam": ja_existiam, "destino": destino}
print(resultado)
dbutils.notebook.exit(json.dumps(resultado))
