"""Gold · taxa de conversão histórica por empresa, por CNAE e geral (componente histórico da nota, PRD §2.6).

taxa = leads com oportunidade ganha ÷ leads, por CNPJ válido, por CNAE (da BrasilAPI) e no geral.
histórico = a taxa escalada para 0–100 entre os grupos do mesmo nível (min-max); com um grupo só, ou
todos iguais, fica 50. A fila usa a empresa; sem histórico da empresa, o CNAE; sem nenhum, o geral.
"""
from pyspark import pipelines as dp
from pyspark.sql import Window
from pyspark.sql import functions as F

CAT = spark.conf.get("call_first.catalog")
SILVER = f"{CAT}.{spark.conf.get('call_first.schema_silver')}"


@dp.materialized_view(
    name="historico_conversao",
    comment="Taxa de conversão (leads com oportunidade ganha ÷ leads) por CNPJ, por CNAE e geral, "
            "com o componente histórico de 0 a 100. Gold.",
)
@dp.expect("historico_na_escala", "historico BETWEEN 0 AND 100")
def historico_conversao():
    ganhou = (spark.read.table(f"{SILVER}.oportunidades").where("estagio = 'ganha'")
              .select("lead_id").distinct().withColumn("ganhou", F.lit(1)))
    base = (spark.read.table(f"{SILVER}.leads").where("lead_id IS NOT NULL")
            .join(ganhou, "lead_id", "left")
            .select("lead_id", F.coalesce("ganhou", F.lit(0)).alias("ganhou"),
                    F.when(F.col("cnpj_valido"), F.col("cnpj_norm")).alias("cnpj"),
                    F.col("cnae").cast("string").alias("cnae")))

    def nivel(nome, chave):
        df = base if chave is None else base.where(F.col(chave).isNotNull())
        grupo = [F.lit("geral").alias("chave")] if chave is None else [F.col(chave).alias("chave")]
        return (df.groupBy(*grupo)
                .agg(F.count("*").alias("leads"), F.sum("ganhou").alias("ganhas"))
                .withColumn("nivel", F.lit(nome)))

    t = (nivel("cnpj", "cnpj").unionByName(nivel("cnae", "cnae")).unionByName(nivel("geral", None))
         .withColumn("taxa", F.col("ganhas") / F.col("leads")))
    w = Window.partitionBy("nivel")
    mn, mx = F.min("taxa").over(w), F.max("taxa").over(w)
    return t.withColumn(
        "historico",
        F.when(mx == mn, F.lit(50.0)).otherwise((F.col("taxa") - mn) / (mx - mn) * 100),
    ).select("nivel", "chave", "leads", "ganhas", "taxa", "historico")
