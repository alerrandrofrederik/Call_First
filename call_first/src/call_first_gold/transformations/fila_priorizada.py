"""Gold · a fila priorizada de leads (PRD RF-13, RF-14, §2.6, §2.9).

nota = 0,50 × intenção + 0,20 × porte + 0,15 × histórico + 0,15 × recência, de 0 a 100, com as travas:
spam → no máximo 5 e "Descartar"; suporte → no máximo 25 e "Encaminhar ao suporte".
Os 4 componentes ficam em nota_componentes (RNF-08). Lead sem mensagem entra com intenção "sem mensagem"
(componente 20) e próximo passo "Qualificar por contato" (decisão de 2026-11-01, knowledge/decisions).
"""
from pyspark import pipelines as dp
from pyspark.sql import Window
from pyspark.sql import functions as F

CAT = spark.conf.get("call_first.catalog")
SILVER = f"{CAT}.{spark.conf.get('call_first.schema_silver')}"

PESOS = {"intencao": 0.50, "porte": 0.20, "historico": 0.15, "recencia": 0.15}
INTENCAO = {"compra imediata": 100, "pesquisa": 40, "suporte": 10, "spam": 0}
PORTE = {"DEMAIS": 100, "EMPRESA DE PEQUENO PORTE": 60, "MICRO EMPRESA": 30}
VALOR_DESCONHECIDO = 20
DIAS_RECENCIA = 30


def mapa(col, valores, padrao):
    expr = F.lit(padrao)
    for k, v in valores.items():
        expr = F.when(col == k, F.lit(v)).otherwise(expr)
    return expr


@dp.materialized_view(
    name="fila_priorizada",
    comment="A fila de leads para o vendedor, um lead por linha, com a nota de 0 a 100 e seus 4 componentes. "
            "posicao = ordem da fila (nota desc). Contém dados pessoais: acesso só para o time comercial. Gold.",
)
@dp.expect_all({
    "componentes_preenchidos": "nota_componentes.intencao IS NOT NULL AND nota_componentes.porte IS NOT NULL "
                               "AND nota_componentes.historico IS NOT NULL AND nota_componentes.recencia IS NOT NULL",
    "nota_na_escala": "nota BETWEEN 0 AND 100",
    "trava_spam": "intencao <> 'spam' OR nota <= 5",
    "trava_suporte": "intencao <> 'suporte' OR nota <= 25",
})
def fila_priorizada():
    leads = spark.read.table(f"{SILVER}.leads")
    ia = spark.read.table("ia_formularios_fonte")
    vend = spark.read.table(f"{SILVER}.vendedores").select(
        F.col("id").alias("vendedor_id"), F.col("nome").alias("vendedor"), F.col("regiao").alias("vendedor_regiao"))
    hist = spark.read.table("historico_conversao")
    h_cnpj = hist.where("nivel = 'cnpj'").select(F.col("chave").alias("cnpj_norm"), F.col("historico").alias("_h_cnpj"))
    h_cnae = hist.where("nivel = 'cnae'").select(F.col("chave").alias("_cnae"), F.col("historico").alias("_h_cnae"))
    h_geral = hist.where("nivel = 'geral'").select(F.col("historico").alias("_h_geral"))

    df = (leads
          .join(ia, F.col("ultimo_form_id") == F.col("_ia_form_id"), "left")
          .join(vend, "vendedor_id", "left")
          .join(h_cnpj.withColumnRenamed("cnpj_norm", "_hc"),
                F.col("cnpj_valido") & (F.col("cnpj_norm") == F.col("_hc")), "left")
          .join(h_cnae, F.col("cnae").cast("string") == F.col("_cnae"), "left")
          .crossJoin(h_geral))

    intencao = (F.when(F.col("ultimo_form_id").isNull(), F.lit("sem mensagem"))
                 .otherwise(F.coalesce(F.col("_ia_intencao"), F.lit("aguardando IA"))))
    dias = F.datediff(F.current_date(), F.to_date(F.coalesce("ultimo_recebido_em", "criado_em")))
    comp = F.struct(
        mapa(F.col("intencao"), INTENCAO, VALOR_DESCONHECIDO).cast("double").alias("intencao"),
        mapa(F.col("porte"), PORTE, VALOR_DESCONHECIDO).cast("double").alias("porte"),
        F.round(F.coalesce("_h_cnpj", "_h_cnae", "_h_geral"), 1).alias("historico"),
        F.round(F.greatest(F.lit(0.0), 100 - dias * (100.0 / DIAS_RECENCIA)), 1).alias("recencia"),
    )
    nota_bruta = F.round(sum(F.col(f"nota_componentes.{k}") * p for k, p in PESOS.items())).cast("int")
    nota = (F.when(F.col("intencao") == "spam", F.least(nota_bruta, F.lit(5)))
             .when(F.col("intencao") == "suporte", F.least(nota_bruta, F.lit(25)))
             .otherwise(nota_bruta))
    proximo = (F.when(F.col("intencao") == "spam", F.lit("Descartar"))
                .when(F.col("intencao") == "suporte", F.lit("Encaminhar ao suporte"))
                .when(F.col("intencao") == "sem mensagem", F.lit("Qualificar por contato"))
                .otherwise(F.col("_ia_proximo_passo")))

    out = (df
           .withColumn("lead_id", F.coalesce(F.col("lead_id"), -F.abs(F.xxhash64("email_norm"))))
           .withColumn("intencao", intencao)
           .withColumn("nota_componentes", comp)
           .withColumn("nota", nota)
           .withColumn("proximo_passo", proximo)
           .withColumn("quantidade_num", F.regexp_extract("_ia_quantidade", r"(\d+)", 1).cast("int")))
    ordem = Window.orderBy(F.col("nota").desc(), F.col("nota_componentes.recencia").desc(), F.col("lead_id"))
    return out.withColumn("posicao", F.row_number().over(ordem)).select(
        "posicao", "lead_id", "origem_lead", "nome", F.col("email_norm").alias("email"), "telefone", "cargo",
        "empresa", "cnpj_norm", "cnpj_valido", "porte", "cnae", "cnae_descricao", "uf", "empresa_uf",
        "intencao", F.col("_ia_fonte").alias("fonte_intencao"),
        F.col("_ia_produto").alias("produto"), F.col("_ia_quantidade").alias("quantidade"), "quantidade_num",
        F.col("_ia_prazo").alias("prazo"), F.col("_ia_orcamento").alias("orcamento"),
        F.col("_ia_resumo").alias("resumo"), "proximo_passo",
        "nota", "nota_componentes",
        "vendedor_id", "vendedor", "vendedor_regiao", "status", "origem",
        F.col("ultima_mensagem").alias("mensagem"), "ultimo_form_id", "ultimo_recebido_em",
        "ultimo_canal", "ultimo_utm_source", "ultimo_utm_campaign", "qtd_formularios",
        F.col("_ia_modelo").alias("modelo"), F.col("_ia_versao_prompt").alias("versao_prompt"),
        F.current_timestamp().alias("atualizado_em"),
    )


@dp.temporary_view(name="ia_formularios_fonte")
def ia_formularios_fonte():
    """O resultado da IA (tabela gravada pela tarefa enriquecer_ia), com prefixo para o join."""
    gold = f"{CAT}.{spark.conf.get('call_first.schema_gold')}"
    ia = spark.read.table(f"{gold}.ia_formularios")
    return ia.select(
        F.col("form_id").alias("_ia_form_id"), F.col("intencao").alias("_ia_intencao"),
        F.col("fonte_intencao").alias("_ia_fonte"), F.col("produto").alias("_ia_produto"),
        F.col("quantidade").alias("_ia_quantidade"), F.col("prazo").alias("_ia_prazo"),
        F.col("orcamento").alias("_ia_orcamento"), F.col("resumo").alias("_ia_resumo"),
        F.col("proximo_passo").alias("_ia_proximo_passo"), F.col("modelo").alias("_ia_modelo"),
        F.col("versao_prompt").alias("_ia_versao_prompt"),
    )
