# Fonte: formulários (Supabase Storage, JSON Lines)

Os formulários que os leads enviam, com a mensagem em texto livre e a UTM (origem: `PRD.md` §2.3). Hoje chegam pelos canais site, landing page e evento (origem: o perfil). A mensagem é a entrada da IA, que classifica a intenção e extrai as entidades (origem: `PRD.md` §2.7).

## Campos

Um objeto JSON por linha, com 11 campos e `utm` aninhado (`source`, `campaign`). Os campos, os tipos, a chave `form_id` e as descrições estão em [`metadata/formularios.yaml`](../../metadata/formularios.yaml).

## Acesso

- Supabase Storage pela API S3, com boto3 copiando para um Volume do Unity Catalog e Auto Loader lendo o Volume (origem: `PRD.md` §2.3 e D-02).
- Endpoint, bucket e chaves ficam no `.env` local e em secret scope no Databricks, nunca no repositório.
- No repositório: `storage/formularios/carga_inicial/` e `storage/formularios/incremental/` (o lote da demo ao vivo).

## Entrega

- Um arquivo novo por lote, processado uma única vez (origem: `PRD.md` RF-02).
- Arquivo imutável, sem exclusão; a fonte não garante e-mail normalizado nem CNPJ válido (origem: o perfil; pontos abertos no contrato).

## Na bronze

O notebook [`copiar_formularios.py`](../../call_first/src/bronze/copiar_formularios.py) copia do bucket para o Volume `call_first.bronze.raw` só os arquivos novos, e o pipeline `call_first_etl` ([`formularios.py`](../../call_first/src/call_first_etl/transformations/formularios.py)) ingere cada um uma vez com Auto Loader na streaming table `call_first.bronze.formularios`. Detalhes em [databricks.md](../architecture/databricks.md#tabelas-da-bronze).

Para a demo, subir o lote ao vivo no bucket (`storage/upload_supabase_storage.py --lote`) e rodar o job de novo: só o arquivo novo entra.

## Documentos

- [Data contract](../../contracts/formularios.odcs.yaml), rascunho v0.1.0, com os pontos abertos para o dono da fonte.
- [Perfil dos dados](../../reports/profile_crm_formularios.html).
- `gabarito/intencao_formularios.csv`: a intenção real de cada formulário, só para medir a IA.

## Pegadinhas conhecidas

E-mails com espaços e MAIÚSCULAS, um envio duplicado, `produto_interesse` que diverge da mensagem e o CNPJ com e sem máscara. Os números estão no [perfil](../../reports/profile_crm_formularios.html).
