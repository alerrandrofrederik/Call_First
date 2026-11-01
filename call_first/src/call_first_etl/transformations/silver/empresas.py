"""Silver · cadastro da empresa pela BrasilAPI, um CNPJ por linha.

Vem do cache cru bronze.cnpj_api: a resposta 200 mais recente de cada CNPJ (PRD RF-03, RF-08).
"""
from pyspark import pipelines as dp
from pyspark.sql import Window
from pyspark.sql import functions as F

CAT = spark.conf.get("call_first.catalog")
BRONZE = f"{CAT}.{spark.conf.get('call_first.schema_bronze')}"
SILVER = f"{CAT}.{spark.conf.get('call_first.schema_silver')}"

CAMPOS = """
    razao_social STRING, nome_fantasia STRING, porte STRING, codigo_porte INT,
    cnae_fiscal BIGINT, cnae_fiscal_descricao STRING, uf STRING, municipio STRING,
    descricao_situacao_cadastral STRING, data_inicio_atividade STRING
"""


@dp.materialized_view(
    name=f"{SILVER}.empresas",
    comment="Cadastro da empresa na Receita, via BrasilAPI, um CNPJ por linha. Silver.",
)
@dp.expect("porte_presente", "porte IS NOT NULL")
def empresas():
    ultima = Window.partitionBy("cnpj").orderBy(F.col("_ingerido_em").desc())
    return (
        spark.read.table(f"{BRONZE}.cnpj_api")
        .where("status_http = 200")
        .withColumn("_n", F.row_number().over(ultima)).where("_n = 1")
        .withColumn("j", F.from_json("resposta", CAMPOS))
        .select(
            "cnpj", "j.razao_social", "j.nome_fantasia", "j.porte", "j.codigo_porte",
            F.col("j.cnae_fiscal").alias("cnae"), F.col("j.cnae_fiscal_descricao").alias("cnae_descricao"),
            "j.uf", "j.municipio", F.col("j.descricao_situacao_cadastral").alias("situacao_cadastral"),
            F.to_date("j.data_inicio_atividade").alias("data_inicio_atividade"),
            F.col("_ingerido_em").alias("consultado_em"),
        )
    )
