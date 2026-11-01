# call_first_etl

O código do pipeline declarativo `call_first_etl`. Um dataset por arquivo em `transformations/`.

| Arquivo | Dataset | Camada |
|---|---|---|
| `transformations/bronze/formularios.py` | `<catálogo>.bronze.formularios` (streaming table, Auto Loader) | bronze |
| `transformations/silver/crm.py` | `silver.vendedores`, `produtos`, `oportunidades`, `interacoes` e a view privada `leads_crm` | silver |
| `transformations/silver/formularios.py` | `silver.formularios` | silver |
| `transformations/silver/empresas.py` | `silver.empresas` (BrasilAPI) | silver |
| `transformations/silver/leads.py` | `silver.leads`, um lead por e-mail normalizado | silver |

As regras de limpeza (e-mail, CNPJ, DDD) ficam em `utilities/limpeza.py`, usadas também pela tarefa `consultar_cnpj`.

O pipeline roda dentro do job `bronze_ingest` (`resources/bronze_ingest.job.yml`), depois da tarefa que copia os
arquivos do Supabase Storage para o Volume `raw`. Para rodar só o pipeline:

```bash
databricks bundle run call_first_etl -t dev -p pessoal
```
