# Knowledge

Tudo o que o projeto aprende fica aqui, uma página por assunto, na subpasta do tema. Antes de decidir algo, leia a página do assunto. Ao aprender algo novo, atualize a página existente ou crie uma na subpasta certa e liste-a abaixo.

Regras:

- Cada fato traz a origem (comando, arquivo ou relatório).
- Números de perfil e de qualidade não são copiados: linke o relatório em [`reports/`](../reports/).
- O repositório é público: nada de e-mails, URLs de workspace, credenciais ou dados pessoais.

## Subpastas

| Pasta | O que guarda |
|---|---|
| [`architecture/`](architecture/) | Plataforma, ambientes, camadas e onde cada coisa vive |
| [`business/`](business/) | Glossário, regras de negócio e stakeholders |
| [`decisions/`](decisions/) | Registro de decisões, tomadas e em aberto |
| [`incidents/`](incidents/) | Registro de incidentes (entradas da skill `incident`) |
| [`sources/`](sources/) | Uma página por fonte de dados |

## Páginas

- [architecture/databricks.md](architecture/databricks.md): workspace, perfil do CLI, catálogo, schemas e volumes
- [architecture/pipeline.md](architecture/pipeline.md): papéis do Supabase (OLTP) e do Databricks (lakehouse) e o fluxo medalhão
- [business/glossary.md](business/glossary.md): termos e regras de negócio confirmados nos dados
- [decisions/decision-log.md](decisions/decision-log.md): decisões tomadas e em aberto
- [incidents/incident-log.md](incidents/incident-log.md): incidentes de execução
- [sources/rystore.md](sources/rystore.md): fonte RYStore (varejo)

## Veja também

- [Runbook](../docs/runbook.md) e [guias](../docs/guides/): os comandos e as tarefas repetidas.
- [Produtos de dados](../docs/data-products/fato_vendas/README.md): o que a gold serve aos consumidores, com os contratos.
- [Site de documentação](../docs/site/index.html), gerado do repositório por `tools/site/build_site.py`.

