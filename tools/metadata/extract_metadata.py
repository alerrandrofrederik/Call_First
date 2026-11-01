"""Extrai os fatos técnicos dos metadados das fontes crm e formularios.

Lê os dados, nunca os altera, e escreve um esqueleto YAML por fonte com o nome,
o tipo e a chave de cada coluna. As descrições ficam vazias: elas vêm dos
documentos da fonte e são preenchidas à mão (skill metadata).

Uso (na raiz do repo):
    uv run --no-project --with "psycopg[binary]" python tools/metadata/extract_metadata.py <pasta_saida>

CRM: conexão somente leitura no Supabase Postgres com as variáveis
host/port/database/user/password do .env (nenhuma é impressa).
Formulários: os arquivos JSONL de storage/formularios/, cada valor lido como texto.
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

PG_TYPES = {
    "integer": "integer", "bigint": "integer", "smallint": "integer",
    "numeric": "decimal", "text": "string", "character": "string", "character varying": "string",
    "boolean": "boolean", "timestamp with time zone": "timestamp", "timestamp without time zone": "timestamp",
    "date": "date",
}
ISO_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2}|Z)$")


def read_env(path):
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def crm_tables():
    import psycopg
    env = read_env(REPO / ".env")
    with psycopg.connect(host=env["host"], port=env["port"], dbname=env["database"],
                         user=env["user"], password=env["password"], connect_timeout=20) as conn:
        conn.read_only = True
        cur = conn.cursor()
        cur.execute("""
            select c.table_name, c.column_name, c.data_type, c.is_nullable,
                   c.character_maximum_length, c.numeric_precision, c.numeric_scale
            from information_schema.columns c
            join information_schema.tables t
              on t.table_schema = c.table_schema and t.table_name = c.table_name and t.table_type = 'BASE TABLE'
            where c.table_schema = 'crm'
            order by c.table_name, c.ordinal_position""")
        cols = cur.fetchall()
        cur.execute("""
            select k.table_name, k.column_name
            from information_schema.table_constraints tc
            join information_schema.key_column_usage k
              on k.constraint_name = tc.constraint_name and k.table_schema = tc.table_schema
            where tc.table_schema = 'crm' and tc.constraint_type = 'PRIMARY KEY'""")
        pks = set(cur.fetchall())
    tables = {}
    for t, c, typ, nullable, length, prec, scale in cols:
        tables.setdefault(t, []).append({
            "name": c, "type": PG_TYPES.get(typ, typ), "key": (t, c) in pks,
            "physical": f"{typ}({length})" if length else (f"{typ}({prec},{scale})" if typ == "numeric" and prec else typ),
            "required": nullable == "NO",
        })
    return tables


def text_type(values):
    vals = [v for v in values if v is not None]
    if vals and all(ISO_TS.match(v) for v in vals):
        return "timestamp"
    return "string"


def form_columns():
    rows = []
    for f in sorted((REPO / "storage/formularios").rglob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                # parse_float/parse_int como str: nenhum valor muda de forma, IDs mantêm zeros
                rows.append(json.loads(line, parse_float=str, parse_int=str))
    names = list(dict.fromkeys(k for r in rows for k in r))
    cols = []
    for n in names:
        vals = [r.get(n) for r in rows]
        if any(isinstance(v, dict) for v in vals):
            subs = list(dict.fromkeys(k for v in vals if isinstance(v, dict) for k in v))
            cols.append({"name": n, "type": "object", "key": False, "required": all(n in r for r in rows),
                         "fields": [{"name": s, "type": text_type([None if v.get(s) is None else str(v.get(s)) for v in vals if isinstance(v, dict)])}
                                    for s in subs]})
        else:
            cols.append({"name": n, "type": text_type([None if v is None else str(v) for v in vals]),
                         "key": n == "form_id", "required": all(r.get(n) is not None for r in rows)})
    return {"formularios": cols}, len(rows)


def q(s):
    return json.dumps(s, ensure_ascii=False)


def write_yaml(path, source, tables):
    out = [f"# Esqueleto gerado por tools/metadata/extract_metadata.py: nomes, tipos e chaves vêm dos dados.",
           f"source: {source}", "tables:"]
    for t, cols in tables.items():
        out += ["", f"  - name: {t}", '    description: ""', "    columns:"]
        for c in cols:
            out.append(f"      - name: {c['name']}")
            out.append(f"        type: {c['type']}")
            if c.get("key"):
                out.append("        key: true")
            out.append(f"        # physical: {c.get('physical', 'json')} · required: {str(c['required']).lower()}")
            out.append('        description: ""')
            for s in c.get("fields", []):
                out += [f"        # campo {c['name']}.{s['name']}: {s['type']}"]
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "metadata"
    outdir.mkdir(parents=True, exist_ok=True)
    crm = crm_tables()
    forms, n = form_columns()
    write_yaml(outdir / "crm.skeleton.yaml", "crm", crm)
    write_yaml(outdir / "formularios.skeleton.yaml", "formularios", forms)
    print(f"crm: {len(crm)} tabelas, {sum(len(c) for c in crm.values())} colunas")
    print(f"formularios: {n} linhas, {len(forms['formularios'])} campos")


if __name__ == "__main__":
    main()
