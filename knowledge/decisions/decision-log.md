# Registro de decisões

Uma linha por decisão. As decisões de arquitetura do produto (D-01 a D-05) estão no `PRD.md` §2.8 e não são repetidas aqui.

## Tomadas

| Data | Decisão | Motivo | Origem |
|---|---|---|---|
| 2026-11-01 | Metadados em `metadata/<fonte>.yaml`, contratos em `contracts/<fonte>.odcs.yaml`, script de extração em `tools/metadata/` | O repo não tinha pasta para isso; uma pasta por tipo de artefato | Engenheiro de dados, nesta sessão |
| 2026-11-01 | As descrições dos metadados vêm só de `supabase/01_schema.sql` e `PRD.md` | Documentos indicados pelo engenheiro de dados (skill `metadata`) | Engenheiro de dados, nesta sessão |
| 2026-11-01 | Dono e suporte das fontes ficam como papéis genéricos (`crm-owner`, `formularios-owner`) até a reunião | Os documentos não nomeiam o dono, e o repo é público | Engenheiro de dados, nesta sessão |
| 2026-11-01 | Contratos em ODCS v3.1.0, validados com `datacontract lint` | Formato da skill `contract` | [`contracts/`](../../contracts/) |
| 2026-11-01 | Bronze: `crm_leads` incremental por `atualizado_em`, as outras tabelas do CRM em carga completa; formulários por Auto Loader sobre o Volume `raw` | Só `leads` tem coluna de atualização (contrato crm, P-06); `PRD.md` D-02 | Engenheiro de dados, nesta sessão |
| 2026-11-01 | Silver: CNPJ inválido, DDD inexistente e interação repetida são **sinalizados** (flags + expectations em modo aviso), não removidos; só o envio repetido em até 5 minutos sai (RF-07) | Os pontos P-03, P-04 e P-05 ainda estão em aberto com o dono da fonte; remover agora perderia dado que pode ser legítimo | Engenheiro de dados, nesta sessão |
| 2026-11-01 | Silver: lead só de formulário fica com `lead_id` nulo e `origem_lead = 'formulario'`; a chave da silver é `email_norm` | O ID gerado é da gold (`PRD.md` §2.9) | Engenheiro de dados, nesta sessão |
| 2026-11-01 | BrasilAPI entra junto com a silver: cache cru em `bronze.cnpj_api`, só CNPJs com DV válido | `PRD.md` RF-03, RF-08, D-03 | Engenheiro de dados, nesta sessão |

## Em aberto

Pontos para a reunião com o dono de cada fonte. A lista completa e atualizada fica em `customProperties.openPoints` de cada contrato.

| Fonte | Ponto | Contrato |
|---|---|---|
| plataforma | Os targets `dev` e `prod` do bundle usam os mesmos schemas `bronze`, `silver` e `gold`: separar (outro catálogo ou prefixo) ou aceitar no workshop? | [databricks.md](../architecture/databricks.md) |
| crm, formularios | Dono, canal de suporte e prazo de aviso de mudança | P-01, P-02 |
| crm | CNPJ num formato só e validado na origem? | [crm](../../contracts/crm.odcs.yaml) P-03 |
| crm | Interações 336 e 337: duplicata ou duas reuniões? | [crm](../../contracts/crm.odcs.yaml) P-04 |
| crm | Validar o DDD do telefone ou só sinalizar? | [crm](../../contracts/crm.odcs.yaml) P-05 |
| crm | Carga completa das tabelas sem `atualizado_em` ou a fonte adiciona a coluna? | [crm](../../contracts/crm.odcs.yaml) P-06 |
| crm | Como uma exclusão física chega | [crm](../../contracts/crm.odcs.yaml) P-07 |
| crm | Lead sem vendedor é sempre lead novo não distribuído? | [crm](../../contracts/crm.odcs.yaml) P-08 |
| formularios | Arquivos imutáveis e `form_id` sem repetição entre arquivos | [formularios](../../contracts/formularios.odcs.yaml) P-03 |
| formularios | E-mail normalizado, duplo clique, CNPJ e DDD validados no site? | [formularios](../../contracts/formularios.odcs.yaml) P-04, P-05, P-07, P-08 |
| formularios | O campo `produto_interesse` continua no formulário? | [formularios](../../contracts/formularios.odcs.yaml) P-06 |
| formularios | Quem mantém a lista de canal e de UTM | [formularios](../../contracts/formularios.odcs.yaml) P-09 |
