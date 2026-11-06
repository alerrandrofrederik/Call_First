# Pipeline: Supabase (OLTP) e Databricks (lakehouse)

## Papéis

- **Supabase** é o lado operacional: o CRM no Postgres (schema `crm`) e os formulários no Storage. A plataforma só lê, com usuário e chaves somente leitura (origem: `PRD.md` §2.3 e RNF-03).
- **Databricks** é o lakehouse: ingere, limpa, integra, aplica a IA e serve a fila priorizada, tudo no Unity Catalog (origem: `PRD.md` §2.8 e RNF-04). Detalhes em [databricks.md](databricks.md).
- **BrasilAPI** completa o cadastro da empresa pelo CNPJ, com cache das respostas (origem: `PRD.md` §2.3 e D-03).

## Fluxo medalhão

| De | Para | Como | Origem |
|---|---|---|---|
| Postgres `crm` | bronze | JDBC pelo Session pooler, `leads` incremental por `atualizado_em` | `PRD.md` RF-01, D-01 |
| Storage (formulários) | Volume `bronze.raw` → bronze | boto3 copia só os arquivos novos, Auto Loader ingere cada um uma vez | `PRD.md` RF-02, D-02 |
| BrasilAPI | bronze | só CNPJs que ainda não estão no cache | `PRD.md` RF-03, D-03 |
| bronze | silver | CNPJ com 14 dígitos e DV validado, e-mail normalizado, deduplicação CRM × formulários, enriquecimento, expectations | `PRD.md` RF-05 a RF-09 |
| silver | gold | AI Functions (intenção, entidades, resumo) e a nota de 0 a 100 | `PRD.md` RF-10 em diante, §2.6, §2.7 |
| gold | consumo | painel e Genie, ainda não construídos | `PRD.md` RF-15, RF-16; `README.md` "Onde estamos" |

A bronze guarda o dado como veio, com as colunas técnicas `_fonte`, `_arquivo` e `_ingerido_em` (origem: `PRD.md` RF-04).

## Contratos com as fontes

O que cada fonte entrega e garante está nos contratos: [crm](../../contracts/crm.odcs.yaml) e [formularios](../../contracts/formularios.odcs.yaml). As páginas das fontes estão em [`sources/`](../sources/).
