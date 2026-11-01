# Fonte: CRM (Supabase Postgres, schema `crm`)

O CRM da Atlas Software, empresa fictícia do workshop. Guarda os leads, o time de vendas, o catálogo de produtos, as oportunidades e as interações. Dados sintéticos, gerados com seed fixa (origem: `PRD.md` §5).

## Tabelas

`vendedores`, `produtos`, `leads`, `oportunidades` e `interacoes`. As colunas, os tipos, as chaves e as descrições estão em [`metadata/crm.yaml`](../../metadata/crm.yaml), extraídos por [`tools/metadata/extract_metadata.py`](../../tools/metadata/extract_metadata.py).

## Acesso

- Supabase Postgres pelo **Session pooler** (porta 5432), porque a conexão direta é só IPv6 (origem: `PRD.md` D-01).
- Usuário de banco **somente leitura**, só com SELECT no schema `crm` (origem: `supabase/01_schema.sql`, `PRD.md` RNF-03).
- Host e credenciais ficam no `.env` local e em secret scope no Databricks, nunca no repositório.

## Entrega

- `leads`: incremental por `atualizado_em`, que um trigger grava em todo UPDATE (origem: `supabase/01_schema.sql`, `PRD.md` RF-01).
- `oportunidades`, `interacoes`, `vendedores` e `produtos`: não têm coluna de atualização, então a proposta é carga completa (origem: o perfil; ponto aberto P-06 no contrato).
- Não há marcação de exclusão em nenhuma tabela (origem: o perfil).

## Na bronze

Tabelas `call_first.bronze.crm_<tabela>`, escritas pelo notebook [`ingerir_crm.py`](../../call_first/src/bronze/ingerir_crm.py) do job `bronze_ingest`: `crm_leads` em append pela marca de `atualizado_em`, as outras 4 substituídas a cada execução. Detalhes em [databricks.md](../architecture/databricks.md#tabelas-da-bronze).

## Documentos

- [Data contract](../../contracts/crm.odcs.yaml), rascunho v0.1.0, com os pontos abertos para o dono da fonte.
- [Perfil dos dados](../../reports/profile_crm_formularios.html): formatos, nulos, duplicatas, CNPJ, relações e achados.
- `supabase/01_schema.sql`: o DDL da fonte.

## Pegadinhas conhecidas

O CNPJ chega com e sem máscara e com valores inválidos, e há uma interação registrada duas vezes. Os números estão no [perfil](../../reports/profile_crm_formularios.html).
