# Databricks: workspace, catálogo, schemas e volumes

## Workspace e perfil do CLI

- Use sempre o perfil **`pessoal`** do Databricks CLI (`-p pessoal`). O perfil `DEFAULT` é de outro workspace e outra conta e não pode ser usado (origem: `CLAUDE.md`; `databricks auth profiles`, 2026-11-01).
- A URL do workspace fica na configuração local do CLI (`~/.databrickscfg`), nunca no repositório.

## Catálogo `call_first`

Todo objeto do projeto fica no catálogo `call_first` do Unity Catalog (origem: `CLAUDE.md`).

| Schema | Papel | Conteúdo em 2026-11-01 |
|---|---|---|
| `bronze` | dado como veio das fontes, mais colunas técnicas (`PRD.md` RF-04) | volume `raw`, nenhuma tabela |
| `silver` | dado limpo, deduplicado e enriquecido (`PRD.md` §2.4) | vazio |
| `gold` | IA e nota de prioridade, pronto para o negócio (`PRD.md` §2.4 e §2.9) | vazio |
| `default` | criado automaticamente | vazio |
| `information_schema` | criado automaticamente pelo sistema | |

Origem do conteúdo: `databricks schemas list`, `tables list` e `volumes list` com `-p pessoal`, 2026-11-01.

## Volumes

| Volume | Tipo | Uso |
|---|---|---|
| `call_first.bronze.raw` | MANAGED | pouso dos arquivos copiados do Supabase Storage antes do Auto Loader (`PRD.md` D-02) |

## Bundle

O código e os recursos do Databricks são publicados pelo bundle em [`call_first/`](../../call_first/databricks.yml), feito a partir do template `default-python`:

- targets `dev` (padrão, `mode: development`) e `prod`, os dois no catálogo `call_first`;
- variáveis `schema_bronze`, `schema_silver` e `schema_gold`, com padrão `bronze`, `silver` e `gold`;
- dev e prod usam os mesmos schemas, então um deploy em dev grava nas tabelas de prod (decisão em aberto, ver o [registro de decisões](../decisions/decision-log.md));
- o pipeline `call_first_etl` e o `sample_job` ainda rodam o código de exemplo do template.

Validação: `databricks bundle validate --strict -t dev -p pessoal` e `-t prod` passaram em 2026-11-01.
