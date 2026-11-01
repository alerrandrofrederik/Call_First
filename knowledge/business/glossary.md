# Glossário e regras de negócio

Termos e regras confirmados nos documentos ou nos dados. Cada um traz a origem.

## Termos

| Termo | Significado | Origem |
|---|---|---|
| Lead | Contato com potencial de compra | `PRD.md` §6 |
| Medalhão | Organização em camadas bronze (cru), silver (tratado) e gold (pronto para o negócio) | `PRD.md` §6 |
| Auto Loader | Ingestão incremental de arquivos no Databricks | `PRD.md` §6 |
| AI Functions | Funções SQL do Databricks que chamam LLMs (`ai_classify`, `ai_extract`, `ai_query`) | `PRD.md` §6 |
| Genie | Interface de perguntas em linguagem natural sobre tabelas | `PRD.md` §6 |
| Session pooler | Porta de entrada do Supabase que aceita conexões IPv4 | `PRD.md` §6 |
| Backtest | Aplicar a regra ao histórico para medir se ela teria acertado | `PRD.md` §6 |
| Atlas Software | Empresa fictícia que vende 5 produtos por assinatura, com 8 vendedores divididos por região e segmento | `PRD.md` §1.1 |

## Regras de negócio

| Regra | Origem |
|---|---|
| Intenção da mensagem: `compra imediata`, `pesquisa`, `suporte` ou `spam` | `PRD.md` RF-10 |
| Nota = 0,50 × intenção + 0,20 × porte + 0,15 × histórico + 0,15 × recência, de 0 a 100 | `PRD.md` §2.6 |
| `spam` tem nota máxima de 5 e próximo passo "Descartar"; `suporte`, nota máxima de 25 e "Encaminhar ao suporte" | `PRD.md` §2.6 |
| Mensagem vazia ou com menos de 5 caracteres é `spam`, sem chamar a IA | `PRD.md` §2.7 |
| Deduplicação de leads pelo e-mail normalizado; fica o cadastro do CRM mais a mensagem mais recente do formulário | `PRD.md` §2.6 |
| Envios idênticos (mesmo e-mail e mesma mensagem em até 5 minutos) são removidos | `PRD.md` RF-07 |
| Conversão lead → venda = oportunidades ganhas ÷ leads | `PRD.md` §1.3 |

## Confirmado nos dados

| Fato | Origem |
|---|---|
| Oportunidades só existem para leads com status `qualificado` ou `contatado` | [perfil](../../reports/profile_crm_formularios.html) |
| Os leads sem vendedor têm todos status `novo` (ponto aberto P-08 no contrato do CRM) | [perfil](../../reports/profile_crm_formularios.html) |
| `fechada_em` está preenchida só nas oportunidades `ganha` ou `perdida`, e `motivo_perda` só nas `perdida` | [perfil](../../reports/profile_crm_formularios.html) |
| Um mesmo lead pode mandar mais de um formulário com conteúdo diferente; a silver fica com um lead e a mensagem mais recente (`qtd_formularios` conta os envios) | `silver.leads`, 2026-11-01 |
| A IA erra a intenção em poucos casos, todos spam lidos como pesquisa; o número exato está em `gold.avaliacao_ia` | `gold.avaliacao_ia`, 2026-11-01 |
| Os 30 CNPJs válidos têm porte `DEMAIS` na Receita; 29 estão com situação `ATIVA` e 1 `BAIXADA`. Com esses dados, o componente porte da nota (`PRD.md` §2.6) é o mesmo para todo lead com CNPJ válido | `silver.empresas` (BrasilAPI), 2026-11-01 |
