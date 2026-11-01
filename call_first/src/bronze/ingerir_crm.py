# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze · ingerir o CRM (Supabase Postgres, schema `crm`)
# MAGIC
# MAGIC Grava cada tabela do CRM como veio em `<catálogo>.<schema>.crm_<tabela>`, com as colunas técnicas
# MAGIC `_fonte` e `_ingerido_em` (PRD RF-04). Como está no contrato `contracts/crm.odcs.yaml`:
# MAGIC
# MAGIC | Tabela | Carga |
# MAGIC |---|---|
# MAGIC | `leads` | incremental: só as linhas com `atualizado_em` maior que o maior já gravado (PRD RF-01), em append |
# MAGIC | `vendedores`, `produtos`, `oportunidades`, `interacoes` | completa: a tabela é substituída (sem coluna de atualização, ponto aberto P-06) |
# MAGIC
# MAGIC Reexecutar sem mudança no CRM não grava linha nova em `crm_leads` (PRD RNF-01).
# MAGIC Conexão somente leitura; credenciais no secret scope `call_first`.

# COMMAND ----------

dbutils.widgets.text("catalog", "call_first")
dbutils.widgets.text("schema", "bronze")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

# COMMAND ----------

import json

from pyspark.sql import functions as F

spark.conf.set("spark.sql.session.timeZone", "UTC")


def segredo(chave):
    return dbutils.secrets.get("call_first", chave)


def ler(consulta):
    """Lê uma consulta do Postgres pelo data source postgresql do Databricks."""
    return (
        spark.read.format("postgresql")
        .option("host", segredo("pg_host"))
        .option("port", segredo("pg_port"))
        .option("database", segredo("pg_database"))
        .option("user", segredo("pg_user"))
        .option("password", segredo("pg_password"))
        .option("dbtable", f"({consulta}) AS q")
        .load()
    )


def com_colunas_tecnicas(df, tabela):
    return df.withColumn("_fonte", F.lit(f"crm.{tabela}")).withColumn("_ingerido_em", F.current_timestamp())


resultado = {}

# COMMAND ----------

# DBTITLE 1,Carga completa: vendedores, produtos, oportunidades, interacoes
for tabela in ["vendedores", "produtos", "oportunidades", "interacoes"]:
    df = com_colunas_tecnicas(ler(f"SELECT * FROM crm.{tabela}"), tabela)
    (df.write.mode("overwrite").option("overwriteSchema", "true")
       .saveAsTable(f"{catalog}.{schema}.crm_{tabela}"))
    resultado[tabela] = {"carga": "completa", "linhas": spark.table(f"{catalog}.{schema}.crm_{tabela}").count()}

# COMMAND ----------

# DBTITLE 1,Carga incremental: leads por atualizado_em
alvo = f"{catalog}.{schema}.crm_leads"
filtro = ""
if spark.catalog.tableExists(alvo):
    marca = (spark.table(alvo)
             .select(F.date_format(F.max("atualizado_em"), "yyyy-MM-dd HH:mm:ss.SSSSSS").alias("m"))
             .first()["m"])
    if marca:
        filtro = f" WHERE atualizado_em > TIMESTAMPTZ '{marca}+00'"

novos = com_colunas_tecnicas(ler(f"SELECT * FROM crm.leads{filtro}"), "leads")
n_novos = novos.count()
if n_novos:
    novos.write.mode("append").saveAsTable(alvo)
resultado["leads"] = {"carga": "incremental", "watermark": filtro or "primeira carga",
                      "linhas_novas": n_novos, "linhas": spark.table(alvo).count()}

# COMMAND ----------

print(resultado)
dbutils.notebook.exit(json.dumps(resultado))
