"""Prompt fixo do resumo e do próximo passo (PRD RF-12, §2.7).

A versão do prompt e o modelo são gravados em cada linha de gold.ia_formularios, para auditoria.
Mudou o texto? Suba a versão: as linhas antigas continuam com a versão com que foram geradas.
"""

MODELO = "databricks-meta-llama-3-3-70b-instruct"
VERSAO_PROMPT = "v1"

ROTULOS = ["compra imediata", "pesquisa", "suporte", "spam"]
ENTIDADES = ["produto", "quantidade", "prazo", "orcamento"]

PROMPT_RESUMO = (
    "Você ajuda um vendedor B2B da Atlas Software, que vende os produtos Atlas Gestão (ERP), Atlas BI, "
    "Atlas Fiscal, Atlas CRM e Atlas Estoque. Leia a mensagem que um lead enviou e responda em português, "
    "só com JSON: {\"resumo\": \"...\", \"proximo_passo\": \"...\"}. "
    "resumo: até 15 palavras, o que o lead quer, sem inventar nada que não esteja na mensagem. "
    "proximo_passo: uma ação curta para o vendedor, começando com um verbo no infinitivo. "
    "Empresa do lead: {empresa}. Mensagem: {mensagem}"
)

FORMATO_RESPOSTA = (
    '{"type":"json_schema","json_schema":{"name":"resumo_lead","strict":true,"schema":{"type":"object",'
    '"properties":{"resumo":{"type":"string"},"proximo_passo":{"type":"string"}},'
    '"required":["resumo","proximo_passo"]}}}'
)
