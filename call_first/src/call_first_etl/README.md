# call_first_etl

O código do pipeline declarativo `call_first_etl`. Um dataset por arquivo em `transformations/`.

| Arquivo | Dataset | Camada |
|---|---|---|
| `transformations/formularios.py` | `<catálogo>.bronze.formularios` (streaming table, Auto Loader) | bronze |

O pipeline roda dentro do job `bronze_ingest` (`resources/bronze_ingest.job.yml`), depois da tarefa que copia os
arquivos do Supabase Storage para o Volume `raw`. Para rodar só o pipeline:

```bash
databricks bundle run call_first_etl -t dev -p pessoal
```
