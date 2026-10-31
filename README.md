# Workshop · Priorização inteligente de leads (Databricks + IA)

Pacote para **criar e restaurar** as fontes de dados no Supabase e testar a conexão com o Databricks.

```
supabase/
  01_schema.sql               schema crm, tabelas, trigger e usuário somente leitura (idempotente)
  02_seed.sql                 carga do CRM: 8 vendedores, 5 produtos, 320 leads, ~110 oportunidades, ~430 interações
  03_novos_leads_ao_vivo.sql  5 leads para inserir DURANTE a demo (carga incremental)
storage/
  formularios/carga_inicial/  151 formulários (JSON Lines) com texto livre
  formularios/incremental/    20 formulários "ao vivo", incluindo as 5 pegadinhas para a IA
  upload_supabase_storage.py  sobe/limpa os arquivos no bucket via API S3
databricks/
  00_teste_conexoes.py        notebook (importar no workspace) que testa as 3 fontes
gabarito/
  intencao_formularios.csv    intenção real de cada mensagem, para medir o acerto do ai_classify
gerar_dados.py                regenera tudo (seed fixa = mesmo resultado sempre)
```

## 1. Banco (Supabase Postgres)

1. Crie o projeto no Supabase, de preferência na região **São Paulo (sa-east-1)**.
2. Em `01_schema.sql`, troque `TROQUE_ESTA_SENHA` pela senha do usuário `databricks_reader`.
3. **SQL Editor** → rode `01_schema.sql` e depois `02_seed.sql`.
4. Confira: `select status, count(*) from crm.leads group by 1;`

**Para restaurar entre ensaios**, rode só o `02_seed.sql` de novo. Ele limpa e recarrega, e as datas são
relativas a `now()`, então o dado sempre parece recente. Rode o `01_schema.sql` apenas se alterar a estrutura.

**Conexão:** no botão **Connect** do dashboard, use o **Session pooler** (porta 5432). A conexão direta do
Supabase é só IPv6, e o pooler aceita IPv4. Pelo pooler, o usuário fica no formato
`databricks_reader.<PROJECT_REF>`. Se esse login falhar, teste primeiro com `postgres.<PROJECT_REF>` para isolar o problema.

## 2. Arquivos (Supabase Storage)

1. **Storage** → **New bucket** → `formularios` (privado).
2. **Project Settings → Storage → S3 Access Keys** → gere o par de chaves e anote endpoint e região.
3. Suba a carga inicial com o script (`--lote` durante a demo; `--limpar` para resetar) ou arraste os arquivos
   no dashboard para a pasta `entrada/`.

```bash
pip install boto3
export SUPABASE_PROJECT_REF=... SUPABASE_REGION=sa-east-1 SUPABASE_S3_KEY_ID=... SUPABASE_S3_SECRET=...
python storage/upload_supabase_storage.py
```

## 3. API (BrasilAPI)

Os leads usam CNPJs de matriz de 30 empresas reais e públicas (Petrobras, WEG, Natura...), todos com dígito
verificador válido, mais 3 CNPJs inválidos de propósito para demonstrar tratamento de erro. O notebook consulta
todos e grava um cache em Volume. **Na demo, leia do cache**: a API pública tem rate limit e pode oscilar.

## 4. Databricks

Importe `databricks/00_teste_conexoes.py` (Workspace → Import), preencha a célula de configuração (ou crie a
secret scope `workshop`) e rode célula a célula. A **primeira célula testa a rede**: rode-a antes de tudo.

> ⚠️ **Free Edition:** a internet de saída é restrita a domínios confiáveis, então Supabase e BrasilAPI podem
> ser bloqueados. Opções: verificar a conta com LinkedIn (libera a internet de saída) ou usar o trial de 14 dias
> numa cloud. Confirme isso **semanas antes** do workshop.

## Pegadinhas planejadas (para o roteiro)

| Onde | O quê | Demonstra |
|---|---|---|
| CRM | CNPJ com e sem máscara | Limpeza na Silver |
| CRM | 3 CNPJs inválidos, leads sem empresa | API retornando 404 e tratamento de erro |
| Formulários | ~25% são leads que já existem no CRM, metade com e-mail em MAIÚSCULAS e com espaços | Deduplicação por e-mail normalizado |
| Formulários | Um envio duplicado (duplo clique) | Deduplicação exata |
| Formulários | `produto_interesse` do formulário diverge do produto citado na mensagem | `ai_extract` lê a intenção real |
| Lote ao vivo | Compra escondida em texto informal, "não é suporte, quero contratar", "comprar solução" para erro (= suporte), "urgente" de estudante, spam com "compre agora" | `ai_classify` acertando onde regra de palavra-chave erra |
| Gabarito | Intenção real de cada formulário | Medir a acurácia da IA ao vivo |
