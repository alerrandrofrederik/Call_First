"""Silver · um lead por e-mail normalizado, juntando CRM e formulários (PRD RF-06, §2.6).

- Chave: email_norm.
- Sobrevivência: o cadastro do CRM quando o e-mail existe no CRM; senão, o do formulário mais recente.
  A mensagem é sempre a do formulário mais recente.
- Lead só de formulário: lead_id nulo e origem_lead = 'formulario' (o ID gerado é decisão da gold, PRD §2.9).
- Empresa: o cadastro da BrasilAPI pelo CNPJ válido; sem CNPJ ou com CNPJ inválido, os campos ficam nulos (RF-08).
"""
from pyspark import pipelines as dp
from pyspark.sql import Window
from pyspark.sql import functions as F

from utilities.limpeza import cnpj_valido

CAT = spark.conf.get("call_first.catalog")
SILVER = f"{CAT}.{spark.conf.get('call_first.schema_silver')}"


@dp.materialized_view(
    name=f"{SILVER}.leads",
    comment="Um lead por e-mail normalizado, CRM e formulários juntos, com a empresa da BrasilAPI. Silver.",
)
@dp.expect("email_presente", "email_norm IS NOT NULL")
@dp.expect("cnpj_valido_quando_ha", "cnpj_norm IS NULL OR cnpj_valido")
def leads():
    crm = spark.read.table("leads_crm")
    forms = spark.read.table(f"{SILVER}.formularios")
    empresas = spark.read.table(f"{SILVER}.empresas")

    recente = Window.partitionBy("email_norm").orderBy(F.col("recebido_em").desc(), F.col("form_id").desc())
    ultimo_form = (
        forms
        .withColumn("qtd_formularios", F.count(F.lit(1)).over(Window.partitionBy("email_norm")))
        .withColumn("_n", F.row_number().over(recente)).where("_n = 1")
        .select(
            "email_norm", "qtd_formularios",
            F.col("form_id").alias("ultimo_form_id"),
            F.col("recebido_em").alias("ultimo_recebido_em"),
            F.col("mensagem").alias("ultima_mensagem"),
            F.col("canal").alias("ultimo_canal"),
            F.col("utm_source").alias("ultimo_utm_source"),
            F.col("utm_campaign").alias("ultimo_utm_campaign"),
            F.col("produto_interesse").alias("ultimo_produto_interesse"),
            F.col("nome").alias("_f_nome"), F.col("telefone").alias("_f_telefone"),
            F.col("empresa").alias("_f_empresa"), F.col("cnpj_norm").alias("_f_cnpj_norm"),
            F.col("ddd_valido").alias("_f_ddd_valido"),
        )
    )

    c = crm.alias("c")
    f = ultimo_form.alias("f")
    tem_crm = F.col("c.id").isNotNull()
    junto = c.join(f, F.col("c.email_norm") == F.col("f.email_norm"), "full_outer")

    def crm_ou_form(col_crm, col_form):
        return F.when(tem_crm, F.col(col_crm)).otherwise(F.col(col_form))

    lead = junto.select(
        F.col("c.id").alias("lead_id"),
        F.when(tem_crm, "crm").otherwise("formulario").alias("origem_lead"),
        F.coalesce("c.email_norm", "f.email_norm").alias("email_norm"),
        crm_ou_form("c.nome_contato", "f._f_nome").alias("nome"),
        crm_ou_form("c.telefone", "f._f_telefone").alias("telefone"),
        crm_ou_form("c.ddd_valido", "f._f_ddd_valido").alias("ddd_valido"),
        F.col("c.cargo").alias("cargo"),
        crm_ou_form("c.empresa", "f._f_empresa").alias("empresa"),
        crm_ou_form("c.cnpj_norm", "f._f_cnpj_norm").alias("cnpj_norm"),
        F.col("c.uf").alias("uf"),
        F.col("c.origem").alias("origem"),
        F.col("c.status").alias("status"),
        F.col("c.vendedor_id").alias("vendedor_id"),
        F.col("c.criado_em").alias("criado_em"),
        F.col("c.atualizado_em").alias("atualizado_em"),
        F.coalesce("f.qtd_formularios", F.lit(0)).alias("qtd_formularios"),
        "f.ultimo_form_id", "f.ultimo_recebido_em", "f.ultima_mensagem", "f.ultimo_canal",
        "f.ultimo_utm_source", "f.ultimo_utm_campaign", "f.ultimo_produto_interesse",
    )

    lead = lead.withColumn("cnpj_valido", cnpj_valido(F.col("cnpj_norm")))
    e = empresas.select(
        F.col("cnpj").alias("_e_cnpj"), "razao_social", "porte", "cnae", "cnae_descricao",
        F.col("uf").alias("empresa_uf"), F.col("municipio").alias("empresa_municipio"), "situacao_cadastral",
    )
    return lead.join(e, (F.col("cnpj_norm") == F.col("_e_cnpj")) & F.col("cnpj_valido"), "left").drop("_e_cnpj")
