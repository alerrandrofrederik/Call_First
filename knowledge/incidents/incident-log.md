# Registro de incidentes

Uma entrada por execução que falhou, escrita pela skill `incident`: o erro, a causa-raiz, as opções e a decisão.

| Data | Job ou pipeline | Erro | Causa-raiz | Decisão | Relatório |
|---|---|---|---|---|---|

Nenhum incidente registrado. O job `bronze_ingest` de dev rodou 8 vezes em 2026-11-01, todas com sucesso, e não rodou depois disso (origem: `databricks jobs list-runs -p pessoal`, 2026-11-06). O CA-08 falhou como critério de aceite, não como execução: ver [databricks.md](../architecture/databricks.md#critérios-de-aceite-com-o-lote-ao-vivo-2026-11-01-prompt-v1).
