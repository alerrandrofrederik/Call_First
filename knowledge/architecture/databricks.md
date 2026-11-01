# Databricks: workspace, catálogo, schemas e volumes

## Workspace e perfil do CLI

- Use sempre o perfil **`pessoal`** do Databricks CLI (`-p pessoal`). O perfil `DEFAULT` é de outro workspace e outra conta e não pode ser usado (origem: `CLAUDE.md`; `databricks auth profiles`, 2026-11-01).
- A URL do workspace fica na configuração local do CLI (`~/.databrickscfg`), nunca no repositório.

## Catálogo `call_first`

Todo objeto do projeto fica no catálogo `call_first` do Unity Catalog (origem: `CLAUDE.md`).

| Schema | Papel | Conteúdo em 2026-11-01 |
|---|---|---|
| `bronze` | dado como veio das fontes, mais colunas técnicas (`PRD.md` RF-04) | volume `raw` e 6 tabelas (ver abaixo) |
| `silver` | dado limpo, deduplicado e enriquecido (`PRD.md` §2.4) | vazio |
| `gold` | IA e nota de prioridade, pronto para o negócio (`PRD.md` §2.4 e §2.9) | vazio |
| `default` | criado automaticamente | vazio |
| `information_schema` | criado automaticamente pelo sistema | |

Origem do conteúdo: `databricks schemas list`, `tables list` e `volumes list` com `-p pessoal`, 2026-11-01.

## Volumes

| Volume | Tipo | Uso |
|---|---|---|
| `call_first.bronze.raw` | MANAGED | pouso dos arquivos copiados do Supabase Storage antes do Auto Loader (`PRD.md` D-02), em `raw/formularios/` |

## Tabelas da bronze

Dado como veio, com `_fonte` e `_ingerido_em` em todas e `_arquivo` nos formulários (`PRD.md` RF-04). Carga como no contrato de cada fonte.

| Tabela | Tipo | Carga | Escrita por |
|---|---|---|---|
| `crm_leads` | Delta | incremental por `atualizado_em`, em append | job `bronze_ingest`, tarefa `ingerir_crm` |
| `crm_vendedores`, `crm_produtos`, `crm_oportunidades`, `crm_interacoes` | Delta | completa, substitui a tabela | job `bronze_ingest`, tarefa `ingerir_crm` |
| `formularios` | streaming table | Auto Loader, cada arquivo uma vez; `_rescued_data` guarda o que não casar com o schema | pipeline `call_first_etl` |

Validação em 2026-11-01: as contagens batem com o [perfil](../../reports/profile_crm_formularios.html), e uma segunda execução do job não gravou nenhuma linha nova (origem: `databricks bundle run bronze_ingest -t dev`, duas vezes).

## Secret scope `call_first`

Credenciais das fontes, gravadas a partir do `.env` local. Só os nomes das chaves ficam aqui: `pg_host`, `pg_port`, `pg_database`, `pg_user`, `pg_password`, `s3_endpoint`, `s3_region`, `s3_access_key_id`, `s3_secret_access_key`, `s3_bucket`. Para trocar um valor: `databricks secrets put-secret call_first <chave> -p pessoal`.

Rede: o compute serverless deste workspace alcança o pooler do Supabase (5432) e o Storage (443) (origem: teste de conexão serverless, 2026-11-01).

## Bundle

O código e os recursos do Databricks são publicados pelo bundle em [`call_first/`](../../call_first/databricks.yml), feito a partir do template `default-python`:

- targets `dev` (padrão, `mode: development`) e `prod`, os dois no catálogo `call_first`;
- variáveis `schema_bronze`, `schema_silver` e `schema_gold`, com padrão `bronze`, `silver` e `gold`;
- dev e prod usam os mesmos schemas, então um deploy em dev grava nas tabelas de prod (decisão em aberto, ver o [registro de decisões](../decisions/decision-log.md));
- job `bronze_ingest` (`resources/bronze_ingest.job.yml`), diário (pausado em dev): `ingerir_crm` em paralelo com `copiar_formularios` → `atualizar_formularios` (o pipeline);
- pipeline `call_first_etl` (serverless), hoje só com a bronze dos formulários;
- o código de exemplo do template (taxis, `sample_job`) foi removido.

Comandos: `databricks bundle deploy -t dev -p pessoal` e `databricks bundle run bronze_ingest -t dev -p pessoal`, a partir de `call_first/`. Só o target `dev` foi publicado até agora.
