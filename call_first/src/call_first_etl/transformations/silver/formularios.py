"""Silver · formulários limpos, sem o envio repetido.

- recebido_em vira timestamp; utm vira utm_source e utm_campaign.
- email_norm, cnpj_norm, cnpj_valido e ddd_valido (PRD RF-05, RF-06; DDD só sinaliza).
- Envio repetido: mesmo e-mail normalizado e mesma mensagem até 5 minutos depois do envio anterior
  sai da tabela; fica o primeiro (PRD RF-07).
"""
from pyspark import pipelines as dp
from pyspark.sql import Window
from pyspark.sql import functions as F

from utilities.limpeza import cnpj_norm, cnpj_valido, ddd_valido, email_norm

CAT = spark.conf.get("call_first.catalog")
BRONZE = f"{CAT}.{spark.conf.get('call_first.schema_bronze')}"
SILVER = f"{CAT}.{spark.conf.get('call_first.schema_silver')}"

JANELA_REPETIDO_SEG = 5 * 60


@dp.materialized_view(
    name=f"{SILVER}.formularios",
    comment="Um formulário por linha, limpo, sem os envios repetidos em até 5 minutos. Silver.",
)
@dp.expect("sem_dado_resgatado", "_rescued_data IS NULL")
@dp.expect("recebido_em_valido", "recebido_em IS NOT NULL")
@dp.expect("cnpj_valido_quando_ha", "cnpj_norm IS NULL OR cnpj_valido")
@dp.expect("ddd_valido", "ddd_valido")
def formularios():
    df = (
        spark.read.table(f"{BRONZE}.formularios")
        .withColumn("recebido_em", F.to_timestamp("recebido_em", "yyyy-MM-dd'T'HH:mm:ssXXX"))
        .withColumn("utm_source", F.col("utm.source"))
        .withColumn("utm_campaign", F.col("utm.campaign"))
        .drop("utm", "_fonte")
        .withColumn("email_norm", email_norm(F.col("email")))
        .withColumn("cnpj_norm", cnpj_norm(F.col("cnpj")))
        .withColumn("cnpj_valido", cnpj_valido(F.col("cnpj_norm")))
        .withColumn("ddd_valido", ddd_valido(F.col("telefone")))
    )
    ordem = Window.partitionBy("email_norm", "mensagem").orderBy("recebido_em", "form_id")
    anterior = F.lag("recebido_em").over(ordem)
    repetido = anterior.isNotNull() & (
        F.col("recebido_em").cast("long") - anterior.cast("long") <= JANELA_REPETIDO_SEG
    )
    return df.withColumn("_repetido", repetido).where(~F.col("_repetido")).drop("_repetido")
