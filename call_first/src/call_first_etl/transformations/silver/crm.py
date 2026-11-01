"""Silver · tabelas do CRM: vendedores, produtos, oportunidades, interacoes e a versão atual de cada lead.

As 4 primeiras chegam inteiras na bronze a cada carga; aqui ficam com as colunas do metadata
(metadata/crm.yaml) e as checagens do contrato (contracts/crm.odcs.yaml) em modo aviso (PRD RF-09).
leads_crm é intermediária: a bronze de leads é append, então guarda só a versão mais recente de cada id.
"""
from pyspark import pipelines as dp
from pyspark.sql import Window
from pyspark.sql import functions as F

from utilities.limpeza import cnpj_norm, cnpj_valido, ddd_valido, email_norm

CAT = spark.conf.get("call_first.catalog")
BRONZE = f"{CAT}.{spark.conf.get('call_first.schema_bronze')}"
SILVER = f"{CAT}.{spark.conf.get('call_first.schema_silver')}"


def bronze(tabela):
    return spark.read.table(f"{BRONZE}.crm_{tabela}").drop("_fonte")


@dp.materialized_view(name=f"{SILVER}.vendedores", comment="O time de vendas, um vendedor por linha. Silver.")
@dp.expect("id_presente", "id IS NOT NULL")
def vendedores():
    return bronze("vendedores")


@dp.materialized_view(name=f"{SILVER}.produtos", comment="Os 5 produtos vendidos por assinatura. Silver.")
@dp.expect("preco_positivo", "preco_mensal > 0")
def produtos():
    return bronze("produtos")


@dp.materialized_view(name=f"{SILVER}.oportunidades", comment="Uma oportunidade de venda por linha. Silver.")
@dp.expect_all({
    "estagio_no_dominio": "estagio IN ('prospeccao','proposta','negociacao','ganha','perdida')",
    "valor_positivo": "valor_estimado > 0",
    "fechada_se_e_so_se_encerrada": "(fechada_em IS NOT NULL) = (estagio IN ('ganha','perdida'))",
    "fechada_depois_de_criada": "fechada_em IS NULL OR fechada_em >= criada_em",
    "motivo_so_se_perdida": "(motivo_perda IS NOT NULL) = (estagio = 'perdida')",
})
def oportunidades():
    return bronze("oportunidades")


@dp.materialized_view(
    name=f"{SILVER}.interacoes",
    comment="Uma interação de um vendedor com um lead por linha. interacao_duplicada sinaliza linhas idênticas "
            "fora o id (ponto aberto P-04 do contrato crm); nada é removido. Silver.",
)
@dp.expect("tipo_no_dominio", "tipo IN ('ligacao','email','reuniao','whatsapp')")
@dp.expect("sem_duplicata", "NOT interacao_duplicada")
def interacoes():
    chave = Window.partitionBy("lead_id", "vendedor_id", "tipo", "ocorrida_em", "resultado")
    return bronze("interacoes").withColumn("interacao_duplicada", F.count(F.lit(1)).over(chave) > 1)


@dp.materialized_view(
    name="leads_crm",
    private=True,
    comment="Versão mais recente de cada lead do CRM, com e-mail e CNPJ normalizados e as flags de validação.",
)
@dp.expect("cnpj_valido_quando_ha", "cnpj_norm IS NULL OR cnpj_valido")
@dp.expect("ddd_valido", "ddd_valido")
def leads_crm():
    ultima = Window.partitionBy("id").orderBy(F.col("atualizado_em").desc(), F.col("_ingerido_em").desc())
    return (
        bronze("leads")
        .withColumn("_n", F.row_number().over(ultima)).where("_n = 1").drop("_n")
        .withColumn("email_norm", email_norm(F.col("email")))
        .withColumn("cnpj_norm", cnpj_norm(F.col("cnpj")))
        .withColumn("cnpj_valido", cnpj_valido(F.col("cnpj_norm")))
        .withColumn("ddd_valido", ddd_valido(F.col("telefone")))
    )
