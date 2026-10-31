"""
Envia os JSON de formulários para o Supabase Storage pela API S3-compatível.

Pré-requisitos:
  pip install boto3
  Supabase > Storage > New bucket: "formularios" (privado)
  Supabase > Project Settings > Storage > S3 Access Keys > New access key

Variáveis de ambiente:
  SUPABASE_PROJECT_REF   ex.: abcdxyzkqwerty
  SUPABASE_REGION        ex.: sa-east-1   (aparece na página de S3 Configuration)
  SUPABASE_S3_KEY_ID
  SUPABASE_S3_SECRET

Uso:
  python upload_supabase_storage.py            # sobe a carga inicial (antes do workshop)
  python upload_supabase_storage.py --lote     # sobe o lote "ao vivo" (durante a demo)
  python upload_supabase_storage.py --limpar   # apaga tudo do bucket (reset entre ensaios)
"""
import os
import sys
from pathlib import Path

import boto3

BUCKET = "formularios"
REF = os.environ["SUPABASE_PROJECT_REF"]
s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{REF}.storage.supabase.co/storage/v1/s3",
    region_name=os.environ.get("SUPABASE_REGION", "sa-east-1"),
    aws_access_key_id=os.environ["SUPABASE_S3_KEY_ID"],
    aws_secret_access_key=os.environ["SUPABASE_S3_SECRET"],
    config=boto3.session.Config(s3={"addressing_style": "path"}),  # Supabase exige path-style
)
pasta = Path(__file__).parent / "formularios"

if "--limpar" in sys.argv:
    objs = s3.list_objects_v2(Bucket=BUCKET).get("Contents", [])
    for o in objs:
        s3.delete_object(Bucket=BUCKET, Key=o["Key"])
    print(f"{len(objs)} objeto(s) removido(s) de {BUCKET}")
    sys.exit()

origem = pasta / ("incremental" if "--lote" in sys.argv else "carga_inicial")
for arq in sorted(origem.glob("*.jsonl")):
    chave = f"entrada/{arq.name}"  # tudo numa pasta só: o Databricks pega o que for novo
    s3.upload_file(str(arq), BUCKET, chave, ExtraArgs={"ContentType": "application/x-ndjson"})
    print(f"enviado: s3://{BUCKET}/{chave}")
