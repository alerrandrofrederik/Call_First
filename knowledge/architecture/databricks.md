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

Também na bronze: `cnpj_api` (Delta, append), a resposta crua da BrasilAPI por CNPJ, escrita pela tarefa `consultar_cnpj`. Só CNPJs com DV válido e ainda não consultados; 200 e 4xx ficam gravados, timeout e 5xx são tentados na próxima execução (`PRD.md` RF-03, RNF-06).

## Tabelas da silver

Materialized views do pipeline `call_first_etl` em `call_first.silver` (`PRD.md` RF-05 a RF-09). As regras de limpeza ficam em [`utilities/limpeza.py`](../../call_first/src/call_first_etl/utilities/limpeza.py). As expectations rodam em modo aviso e ficam no event log do pipeline.

| Tabela | O que guarda |
|---|---|
| `vendedores`, `produtos`, `oportunidades` | as tabelas do CRM com as checagens do contrato |
| `interacoes` | idem, com `interacao_duplicada` (sinaliza, não remove; ponto aberto P-04) |
| `formularios` | um formulário por linha: `recebido_em` timestamp, `utm_source`/`utm_campaign`, `email_norm`, `cnpj_norm`, `cnpj_valido`, `ddd_valido`; sem o envio repetido em até 5 minutos (RF-07) |
| `empresas` | cadastro da BrasilAPI, um CNPJ por linha: razão social, porte, CNAE, UF, município, situação |
| `leads` | um lead por `email_norm`, CRM e formulários juntos: cadastro do CRM quando existe, senão o do formulário mais recente; a última mensagem; a empresa pelo CNPJ válido. Lead só de formulário tem `lead_id` nulo e `origem_lead = 'formulario'` |

`leads_crm` é uma view privada do pipeline (a versão mais recente de cada lead da bronze, que é append) e não aparece no catálogo.

Validação em 2026-11-01 (origem: consultas no SQL warehouse depois de `bundle run bronze_ingest -t dev`, duas vezes): os números batem com o [perfil](../../reports/profile_crm_formularios.html) (duplo clique removido, CNPJs e DDDs inválidos sinalizados, o par de interações marcado, nenhum CNPJ inválido enviado à API), e a segunda execução não fez nenhuma consulta nova nem mudou as contagens.

## Tabelas da gold

Em `call_first.gold` (`PRD.md` RF-10 a RF-14, §2.6, §2.7, §2.9).

| Tabela | Tipo | Escrita por | O que guarda |
|---|---|---|---|
| `ia_formularios` | Delta, MERGE | job `bronze_ingest`, tarefa `enriquecer_ia` | intenção, entidades, resumo e próximo passo por `form_id`; só formulário novo vai para a IA (RNF-05); modelo e versão do prompt em cada linha |
| `historico_conversao` | materialized view | pipeline `call_first_gold` | taxa de conversão por CNPJ, CNAE e geral, e o componente histórico 0–100 (min-max) |
| `fila_priorizada` | materialized view | pipeline `call_first_gold` | um lead por linha, `posicao` na fila, `nota` e `nota_componentes`; contém dados pessoais |
| `avaliacao_ia` | materialized view | pipeline `call_first_gold` | matriz de confusão da intenção contra o gabarito; sem dados pessoais |

- IA: `ai_classify` e `ai_extract` (modelo padrão da Databricks) e `ai_query` com `databricks-meta-llama-3-3-70b-instruct` e o prompt de [`src/gold/prompts.py`](../../call_first/src/gold/prompts.py). Mensagem com menos de 5 caracteres vira `spam` sem IA.
- Gabarito: `gabarito/intencao_formularios.csv` copiado à mão para o Volume `raw/gabarito/` (`databricks fs cp`), lido só por `avaliacao_ia`.
- Validação em 2026-11-01 (origem: consultas no SQL warehouse depois de `bundle run bronze_ingest -t dev`, duas vezes): as travas, a ordem e os 4 componentes conferem em todos os leads; a acurácia está em `gold.avaliacao_ia`; a segunda execução não chamou a IA.

## Secret scope `call_first`

Credenciais das fontes, gravadas a partir do `.env` local. Só os nomes das chaves ficam aqui: `pg_host`, `pg_port`, `pg_database`, `pg_user`, `pg_password`, `s3_endpoint`, `s3_region`, `s3_access_key_id`, `s3_secret_access_key`, `s3_bucket`. Para trocar um valor: `databricks secrets put-secret call_first <chave> -p pessoal`.

Rede: o compute serverless deste workspace alcança o pooler do Supabase (5432), o Storage (443) e a BrasilAPI (443) (origem: testes de conexão serverless, 2026-11-01).

## Bundle

O código e os recursos do Databricks são publicados pelo bundle em [`call_first/`](../../call_first/databricks.yml), feito a partir do template `default-python`:

- targets `dev` (padrão, `mode: development`) e `prod`, os dois no catálogo `call_first`;
- variáveis `schema_bronze`, `schema_silver` e `schema_gold`, com padrão `bronze`, `silver` e `gold`;
- dev e prod usam os mesmos schemas, então um deploy em dev grava nas tabelas de prod (decisão em aberto, ver o [registro de decisões](../decisions/decision-log.md));
- job `bronze_ingest` (`resources/bronze_ingest.job.yml`), diário (pausado em dev): `ingerir_crm` em paralelo com `copiar_formularios` → `consultar_cnpj` → `atualizar_formularios` (pipeline `call_first_etl`) → `enriquecer_ia` → `atualizar_gold` (pipeline `call_first_gold`);
- pipeline `call_first_etl` (serverless): a bronze dos formulários e a silver inteira;
- pipeline `call_first_gold` (serverless): histórico, fila priorizada e avaliação da IA;
- o código de exemplo do template (taxis, `sample_job`) foi removido.

Comandos: `databricks bundle deploy -t dev -p pessoal` e `databricks bundle run bronze_ingest -t dev -p pessoal`, a partir de `call_first/`. Só o target `dev` foi publicado até agora.
