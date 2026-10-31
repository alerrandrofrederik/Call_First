# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Teste das 3 fontes (rode ANTES do workshop)
# MAGIC
# MAGIC | Fonte | Onde | Como o Databricks lê |
# MAGIC |---|---|---|
# MAGIC | Banco | Supabase Postgres (schema `crm`) | Lakehouse Federation (opção A) ou JDBC (opção B) |
# MAGIC | Arquivos | Supabase Storage, bucket `formularios` | boto3 (S3) → Volume do Unity Catalog → Auto Loader |
# MAGIC | API | BrasilAPI `/api/cnpj/v1/{cnpj}` | `requests` + cache em Volume |
# MAGIC
# MAGIC **Por que o Storage passa por um Volume?** Endpoints S3 que não são da AWS (como o Supabase) não podem ser
# MAGIC registrados como *external location* no Unity Catalog, e o compute serverless não aceita configurar `fs.s3a.endpoint`.
# MAGIC Copiar os arquivos novos para um Volume e deixar o Auto Loader trabalhar ali funciona em qualquer edição.

# COMMAND ----------

# DBTITLE 1,Configuração
# Prefira secrets: databricks secrets create-scope workshop  /  databricks secrets put-secret workshop <chave>
def cfg(chave, padrao=None):
    try:
        return dbutils.secrets.get("workshop", chave)
    except Exception:
        return padrao

PROJECT_REF   = cfg("supabase_project_ref", "<PROJECT_REF>")
POOLER_HOST   = cfg("supabase_pooler_host", "aws-0-sa-east-1.pooler.supabase.com")  # Connect > Session pooler
PG_USER       = cfg("supabase_pg_user", f"databricks_reader.{PROJECT_REF}")          # usuário.ref no pooler
PG_PASSWORD   = cfg("supabase_pg_password", "<SENHA>")
S3_REGION     = cfg("supabase_region", "sa-east-1")
S3_KEY_ID     = cfg("supabase_s3_key_id", "<KEY_ID>")
S3_SECRET     = cfg("supabase_s3_secret", "<SECRET>")
S3_ENDPOINT   = f"https://{PROJECT_REF}.storage.supabase.co/storage/v1/s3"
BUCKET        = "formularios"

CATALOGO, SCHEMA = "workshop", "leads"
VOLUME_LANDING = f"/Volumes/{CATALOGO}/{SCHEMA}/landing"

# COMMAND ----------

# DBTITLE 1,1 · A rede deixa sair? (Free Edition restringe internet de saída)
import socket, requests

alvos = {
    "Postgres (pooler)": (POOLER_HOST, 5432),
    "Storage (S3)":      (f"{PROJECT_REF}.storage.supabase.co", 443),
    "BrasilAPI":         ("brasilapi.com.br", 443),
}
for nome, (host, porta) in alvos.items():
    try:
        socket.create_connection((host, porta), timeout=8).close()
        print(f"OK     {nome:20} {host}:{porta}")
    except Exception as e:
        print(f"FALHOU {nome:20} {host}:{porta}  -> {type(e).__name__}: {e}")
# Se algo FALHAR na Free Edition: verifique a conta com LinkedIn (libera internet de saída)
# ou use o trial de 14 dias numa cloud (AWS/Azure/GCP), que não tem essa restrição.

# COMMAND ----------

# DBTITLE 1,Catálogo, schema e volume do workshop
spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOGO}")
spark.sql(f"CREATE SCHEMA  IF NOT EXISTS {CATALOGO}.{SCHEMA}")
spark.sql(f"CREATE VOLUME  IF NOT EXISTS {CATALOGO}.{SCHEMA}.landing")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 · Banco — opção A: Lakehouse Federation (consulta o Supabase sem copiar)

# COMMAND ----------

spark.sql(f"""
CREATE CONNECTION IF NOT EXISTS supabase_pg TYPE postgresql
OPTIONS (host '{POOLER_HOST}', port '5432', user '{PG_USER}', password '{PG_PASSWORD}')
""")
spark.sql("CREATE FOREIGN CATALOG IF NOT EXISTS supabase_crm USING CONNECTION supabase_pg OPTIONS (database 'postgres')")
display(spark.sql("SELECT status, count(*) AS leads FROM supabase_crm.crm.leads GROUP BY status ORDER BY leads DESC"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 · Banco — opção B: JDBC (útil para carga incremental por `atualizado_em`)

# COMMAND ----------

ultima_carga = "1900-01-01"   # no pipeline real, vem do max(atualizado_em) da Bronze
df_leads = (spark.read.format("jdbc")
    .option("url", f"jdbc:postgresql://{POOLER_HOST}:5432/postgres?sslmode=require")
    .option("user", PG_USER).option("password", PG_PASSWORD)
    .option("query", f"SELECT * FROM crm.leads WHERE atualizado_em > '{ultima_carga}'")
    .load())
print(df_leads.count(), "leads lidos via JDBC")
display(df_leads.limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 · Arquivos — Supabase Storage (S3) → Volume

# COMMAND ----------

# MAGIC %pip install boto3 -q

# COMMAND ----------

import os, boto3
from botocore.config import Config

s3 = boto3.client("s3", endpoint_url=S3_ENDPOINT, region_name=S3_REGION,
                  aws_access_key_id=S3_KEY_ID, aws_secret_access_key=S3_SECRET,
                  config=Config(s3={"addressing_style": "path"}))

destino = f"{VOLUME_LANDING}/formularios"
os.makedirs(destino, exist_ok=True)
novos = 0
for obj in s3.list_objects_v2(Bucket=BUCKET, Prefix="entrada/").get("Contents", []):
    alvo = f"{destino}/{os.path.basename(obj['Key'])}"
    if not os.path.exists(alvo):                     # só o que ainda não chegou
        s3.download_file(BUCKET, obj["Key"], alvo)
        novos += 1
        print("copiado:", obj["Key"])
print(f"{novos} arquivo(s) novo(s) em {destino}")

display(spark.read.json(destino).select("form_id", "recebido_em", "empresa", "cnpj", "mensagem").limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 · API — BrasilAPI (valida os CNPJs e já monta o cache)

# COMMAND ----------

import json, re, time

cnpjs = sorted({re.sub(r"\D", "", r.cnpj) for r in spark.table("supabase_crm.crm.leads").select("cnpj").collect() if r.cnpj})
cache_path = f"{VOLUME_LANDING}/cnpj_cache"
os.makedirs(cache_path, exist_ok=True)

ok, falhas = 0, []
for c in cnpjs:
    arq = f"{cache_path}/{c}.json"
    if os.path.exists(arq):
        ok += 1; continue
    r = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{c}", timeout=15)
    if r.status_code == 200:
        with open(arq, "w") as f:
            json.dump(r.json(), f, ensure_ascii=False)
        ok += 1
    else:
        falhas.append((c, r.status_code))
    time.sleep(0.5)   # gentileza com a API pública (há rate limit)

print(f"{ok} CNPJ(s) enriquecidos/cached")
print("Falhas (esperado para 11111111111111, 12345678000100, 00000000000000):", falhas)

display(spark.read.json(cache_path)
        .select("cnpj", "razao_social", "porte", "cnae_fiscal_descricao", "municipio", "uf"))
