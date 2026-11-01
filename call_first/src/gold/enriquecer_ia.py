# Databricks notebook source
# MAGIC %md
# MAGIC # Gold · IA dos formulários (incremental)
# MAGIC
# MAGIC Para cada formulário de `silver.formularios` que ainda não está em `gold.ia_formularios`:
# MAGIC
# MAGIC - mensagem com menos de 5 caracteres → `spam`, sem chamar a IA (PRD §2.7);
# MAGIC - as outras: `ai_classify` (intenção, RF-10), `ai_extract` (produto, quantidade, prazo, orçamento, RF-11)
# MAGIC   e `ai_query` com o prompt fixo de `prompts.py` (resumo e próximo passo, RF-12).
# MAGIC
# MAGIC Só formulário novo vai para a IA: a segunda execução sem dado novo faz 0 chamadas (RNF-05, CA-14).
# MAGIC O modelo e a versão do prompt ficam gravados em cada linha (§2.7). A IA sugere; quem decide é o vendedor.

# COMMAND ----------

dbutils.widgets.text("catalog", "call_first")
dbutils.widgets.text("schema_silver", "silver")
dbutils.widgets.text("schema_gold", "gold")
catalog = dbutils.widgets.get("catalog")
silver = f"{catalog}.{dbutils.widgets.get('schema_silver')}"
gold = f"{catalog}.{dbutils.widgets.get('schema_gold')}"

# COMMAND ----------

import json

from prompts import ENTIDADES, FORMATO_RESPOSTA, MODELO, PROMPT_RESUMO, ROTULOS, VERSAO_PROMPT

alvo = f"{gold}.ia_formularios"
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {alvo} (
  form_id STRING COMMENT 'Chave do formulário (silver.formularios).',
  email_norm STRING COMMENT 'E-mail normalizado do lead que enviou o formulário.',
  intencao STRING COMMENT 'compra imediata, pesquisa, suporte ou spam (RF-10).',
  fonte_intencao STRING COMMENT 'ia (ai_classify) ou regra (mensagem com menos de 5 caracteres).',
  produto STRING COMMENT 'Produto citado na mensagem (ai_extract).',
  quantidade STRING COMMENT 'Quantidade citada na mensagem, como escrita (ai_extract).',
  prazo STRING COMMENT 'Prazo citado na mensagem (ai_extract).',
  orcamento STRING COMMENT 'Orçamento citado na mensagem (ai_extract).',
  resumo STRING COMMENT 'Resumo de até 15 palavras (ai_query).',
  proximo_passo STRING COMMENT 'Próximo passo sugerido ao vendedor (ai_query).',
  modelo STRING COMMENT 'Endpoint do modelo do resumo; ai_classify e ai_extract usam o modelo padrão da Databricks.',
  versao_prompt STRING COMMENT 'Versão do prompt do resumo (src/gold/prompts.py).',
  processado_em TIMESTAMP COMMENT 'Quando a IA processou o formulário.'
) COMMENT 'Resultado da IA por formulário, gravado uma vez por form_id. Gold.'
""")

pendentes = spark.sql(f"""
SELECT f.form_id, f.email_norm, f.mensagem, f.empresa
FROM {silver}.formularios f LEFT ANTI JOIN {alvo} a ON f.form_id = a.form_id
""")
pendentes.createOrReplaceTempView("pendentes")
n_pendentes = pendentes.count()

# COMMAND ----------

if n_pendentes:
    rotulos = ", ".join(f"'{r}'" for r in ROTULOS)
    entidades = ", ".join(f"'{e}'" for e in ENTIDADES)
    prompt = PROMPT_RESUMO.replace("'", "''").replace("{empresa}", "', coalesce(empresa, 'não informada'), '") \
                          .replace("{mensagem}", "', mensagem, '")
    spark.sql(f"""
    CREATE OR REPLACE TEMP VIEW resultado AS
    WITH regra AS (
      SELECT form_id, email_norm, 'spam' AS intencao, 'regra' AS fonte_intencao,
             CAST(NULL AS STRING) produto, CAST(NULL AS STRING) quantidade, CAST(NULL AS STRING) prazo,
             CAST(NULL AS STRING) orcamento, CAST(NULL AS STRING) resumo, 'Descartar' AS proximo_passo
      FROM pendentes WHERE length(trim(coalesce(mensagem, ''))) < 5
    ),
    ia AS (
      SELECT form_id, email_norm,
             ai_classify(mensagem, ARRAY({rotulos})) AS intencao,
             ai_extract(mensagem, ARRAY({entidades})) AS e,
             ai_query('{MODELO}', concat('{prompt}'), responseFormat => '{FORMATO_RESPOSTA}', failOnError => false) AS q
      FROM pendentes WHERE length(trim(coalesce(mensagem, ''))) >= 5
    )
    SELECT * FROM regra
    UNION ALL
    SELECT form_id, email_norm, intencao, 'ia', e.produto, e.quantidade, e.prazo, e.orcamento,
           from_json(q.result, 'resumo STRING, proximo_passo STRING').resumo,
           from_json(q.result, 'resumo STRING, proximo_passo STRING').proximo_passo
    FROM ia
    """)
    # A IA roda uma vez só, dentro do MERGE; as contagens vêm da própria tabela, pela marca desta execução.
    execucao = spark.sql("SELECT current_timestamp() AS t").first()["t"].isoformat()
    m = spark.sql(f"""
    MERGE INTO {alvo} t
    USING (SELECT *, '{MODELO}' AS modelo, '{VERSAO_PROMPT}' AS versao_prompt,
                  TIMESTAMP '{execucao}' AS processado_em
           FROM resultado WHERE intencao IS NOT NULL) s
    ON t.form_id = s.form_id
    WHEN NOT MATCHED THEN INSERT *
    """).first().asDict()
    inseridos = int(m.get("num_inserted_rows", 0))
    sem_resumo = spark.sql(f"""SELECT count(*) FROM {alvo}
                               WHERE processado_em = TIMESTAMP '{execucao}' AND fonte_intencao = 'ia'
                                 AND resumo IS NULL""").first()[0]
else:
    inseridos = sem_resumo = 0

resultado = {"pendentes": n_pendentes, "gravados": inseridos,
             "sem_intencao_tentar_de_novo": n_pendentes - inseridos,
             "sem_resumo": sem_resumo, "total": spark.table(alvo).count(),
             "modelo": MODELO, "versao_prompt": VERSAO_PROMPT}
print(resultado)
dbutils.notebook.exit(json.dumps(resultado))
