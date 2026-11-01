"""Bronze · formulários: Auto Loader sobre os arquivos JSON Lines copiados para o Volume raw.

O dado fica como veio (PRD RF-04): os campos do contrato contracts/formularios.odcs.yaml, sem limpeza,
mais as colunas técnicas _fonte, _arquivo e _ingerido_em. O que não casar com o schema vai para
_rescued_data. Cada arquivo é ingerido uma única vez (PRD RF-02).
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOGO = spark.conf.get("call_first.catalog")
SCHEMA = spark.conf.get("call_first.schema_bronze")
ORIGEM = f"/Volumes/{CATALOGO}/{SCHEMA}/raw/formularios"

SCHEMA_FORMULARIO = """
    form_id STRING, recebido_em STRING, canal STRING, nome STRING, email STRING, telefone STRING,
    empresa STRING, cnpj STRING, produto_interesse STRING, mensagem STRING,
    utm STRUCT<source: STRING, campaign: STRING>,
    _rescued_data STRING
"""


@dp.table(
    name="formularios",
    comment="Formulários dos leads como vieram do Supabase Storage (JSON Lines), um por linha. Bronze.",
)
def formularios():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("rescuedDataColumn", "_rescued_data")
        .option("pathGlobFilter", "*.jsonl")
        .schema(SCHEMA_FORMULARIO)
        .load(ORIGEM)
        .withColumn("_fonte", F.lit("formularios"))
        .withColumn("_arquivo", F.col("_metadata.file_path"))
        .withColumn("_ingerido_em", F.current_timestamp())
    )
