"""Gold · acerto da IA contra o gabarito (PRD CA-07, CA-08, §3.2).

Matriz de confusão: para cada par (intenção real, intenção prevista), quantos formulários. O gabarito
(gabarito/intencao_formularios.csv) fica no Volume raw só para esta medida: ele nunca entra na nota.
Sem dados pessoais (RNF-07).
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F

CAT = spark.conf.get("call_first.catalog")
BRONZE = f"{CAT}.{spark.conf.get('call_first.schema_bronze')}"
GOLD = f"{CAT}.{spark.conf.get('call_first.schema_gold')}"
GABARITO = f"/Volumes/{CAT}/{spark.conf.get('call_first.schema_bronze')}/raw/gabarito/intencao_formularios.csv"


@dp.materialized_view(
    name="avaliacao_ia",
    comment="Matriz de confusão da intenção: intenção real (gabarito) × prevista (IA ou regra), "
            "com a contagem de formulários. Só os formulários que já passaram pela IA. Gold.",
)
def avaliacao_ia():
    gab = (spark.read.option("header", "true").csv(GABARITO)
           .select("form_id", F.col("intencao_real")))
    ia = spark.read.table(f"{GOLD}.ia_formularios").select(
        "form_id", F.col("intencao").alias("intencao_prevista"), "fonte_intencao", "versao_prompt")
    return (ia.join(gab, "form_id", "inner")
            .groupBy("intencao_real", "intencao_prevista", "versao_prompt")
            .agg(F.count("*").alias("formularios"))
            .withColumn("acerto", F.col("intencao_real") == F.col("intencao_prevista")))
