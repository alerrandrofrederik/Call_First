"""
Gerador do dataset do workshop "Priorização inteligente de leads" (Databricks + IA).

Gera, de forma determinística (seed fixa):
  supabase/01_schema.sql            -> schema crm + tabelas + role de leitura (idempotente)
  supabase/02_seed.sql              -> carga do CRM com datas RELATIVAS a now() (sempre "fresco")
  supabase/03_novos_leads_ao_vivo.sql -> inserts para rodar DURANTE a demo (ingestão incremental)
  storage/formularios/carga_inicial/formularios_AAAAMMDD.jsonl
  storage/formularios/incremental/formularios_lote_ao_vivo.jsonl
  gabarito/intencao_formularios.csv -> rótulo verdadeiro de cada mensagem (p/ medir acerto da IA)

Uso:  python3 gerar_dados.py            (datas dos JSON relativas a hoje)
      python3 gerar_dados.py 2026-11-20 (datas relativas à data do workshop)
"""
import csv, json, random, sys, unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

SEED = 42
rnd = random.Random(SEED)
BASE = Path(__file__).parent
REF = datetime.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.now()
REF = REF.replace(hour=9, minute=0, second=0, microsecond=0, tzinfo=timezone(timedelta(hours=-3)))

# ---------------------------------------------------------------- referência
EMPRESAS = [  # empresas reais (CNPJ público de matriz) -> enriquecimento via BrasilAPI
    ("Petrobras", "33000167000101", "RJ"), ("Banco do Brasil", "00000000000191", "DF"),
    ("Magazine Luiza", "47960950000121", "SP"), ("Natura", "71673990000177", "SP"),
    ("Ambev", "07526557000100", "SP"), ("Vale", "33592510000154", "RJ"),
    ("Itaú Unibanco", "60701190000104", "SP"), ("Embraer", "07689002000189", "SP"),
    ("WEG", "84429695000111", "SC"), ("Localiza", "16670085000155", "MG"),
    ("Totvs", "53113791000122", "SP"), ("Lojas Renner", "92754738000162", "RS"),
    ("Caixa", "00360305000104", "DF"), ("Bradesco", "60746948000112", "SP"),
    ("Correios", "34028316000103", "DF"), ("Gerdau", "33611500000119", "RJ"),
    ("Suzano", "16404287000155", "BA"), ("Raia Drogasil", "61585865000151", "SP"),
    ("JBS", "02916265000160", "SP"), ("BRF", "01838723000127", "SC"),
    ("Klabin", "89637490000145", "SP"), ("Marcopolo", "88611835000129", "RS"),
    ("Eletrobras", "00001180000126", "RJ"), ("Sabesp", "43776517000180", "SP"),
    ("Embratel", "33530486000129", "RJ"), ("Positivo", "81243735000148", "PR"),
    ("Tupy", "84683374000149", "SC"), ("Grendene", "89850341000160", "CE"),
    ("CPFL", "02429144000193", "SP"), ("Cielo", "01027058000191", "SP"),
]
CNPJ_INVALIDOS = ["11111111111111", "12345678000100", "00000000000000"]  # testam tratamento de erro

PRODUTOS = [  # empresa fictícia vendedora: Atlas Software
    (1, "Atlas Gestão (ERP)", "ERP", 4800.00),
    (2, "Atlas BI", "Analytics", 2900.00),
    (3, "Atlas Fiscal", "Fiscal", 1900.00),
    (4, "Atlas CRM", "Vendas", 2400.00),
    (5, "Atlas Estoque", "Supply", 2100.00),
]
VENDEDORES = [
    (1, "Carla Mendes", "Sudeste", "Varejo"), (2, "Rafael Lima", "Sudeste", "Indústria"),
    (3, "Juliana Rocha", "Sul", "Indústria"), (4, "Diego Araújo", "Nordeste", "Serviços"),
    (5, "Patrícia Nunes", "Centro-Oeste", "Financeiro"), (6, "Bruno Teixeira", "Sudeste", "Financeiro"),
    (7, "Fernanda Castro", "Sul", "Varejo"), (8, "Lucas Barros", "Nordeste", "Indústria"),
]
NOMES = ["Ana", "Bruno", "Camila", "Daniel", "Eduarda", "Felipe", "Gabriela", "Henrique", "Isabela",
         "João", "Larissa", "Marcos", "Natália", "Otávio", "Paula", "Renato", "Sabrina", "Tiago",
         "Vanessa", "William", "Aline", "Caio", "Débora", "Gustavo", "Helena", "Igor", "Letícia",
         "Mateus", "Priscila", "Rodrigo", "Simone", "Vinícius", "Beatriz", "Leonardo", "Mariana"]
SOBRENOMES = ["Silva", "Santos", "Oliveira", "Souza", "Pereira", "Costa", "Ferreira", "Almeida",
              "Ribeiro", "Carvalho", "Gomes", "Martins", "Rocha", "Moreira", "Cardoso", "Freitas",
              "Barbosa", "Pinto", "Correia", "Dias", "Monteiro", "Lopes", "Vieira", "Batista"]
CARGOS = ["Gerente de TI", "Diretor Financeiro", "Coordenador de Compras", "Analista de Sistemas",
          "CFO", "Gerente de Operações", "Head de Dados", "Supervisor Fiscal", "CIO", "Controller"]
ORIGENS = ["site", "evento", "indicacao", "outbound", "linkedin"]

# mensagens em texto livre: (intenção verdadeira, texto). {p}=produto, {n}=número
MSGS = {
    "compra imediata": [
        "Precisamos de proposta para {n} licenças do {p} ainda este mês, temos orçamento aprovado.",
        "Estamos trocando de sistema e queremos fechar até o fim do trimestre. Podem me ligar hoje?",
        "Urgente: nosso contrato atual vence em 30 dias e queremos migrar para o {p}. Quero orçamento para {n} usuários.",
        "Bom dia, a diretoria aprovou a verba. Gostaria de agendar reunião esta semana para fechar o {p}.",
        "Quero comprar o {p} para {n} filiais. Qual o prazo de implantação? Orçamento de até R$ {v} mil.",
        "Já avaliamos concorrentes e vocês ficaram em primeiro. Me enviem contrato para {n} licenças.",
        "Olá! Temos um projeto de {p} com início previsto para o mês que vem, preciso da proposta comercial com urgência.",
        "Hi, we are the Brazilian subsidiary and need a quote for {n} {p} licenses this quarter.",
    ],
    "pesquisa": [
        "Gostaria de entender melhor como funciona o {p}. Vocês têm material ou webinar?",
        "Estamos começando a estudar opções de {p} para o ano que vem. Podem me enviar uma apresentação?",
        "Qual a diferença entre o {p} e as soluções de mercado? Ainda estamos só pesquisando.",
        "Vi o post de vocês no LinkedIn e fiquei curioso sobre o {p}. Tem trial gratuito?",
        "Somos uma equipe pequena avaliando ferramentas, sem prazo definido. Quanto custa mais ou menos o {p}?",
        "Preciso montar um benchmark de fornecedores de {p} para apresentar internamente no ano que vem.",
        "Vocês integram com SAP? Estamos mapeando possibilidades, nada decidido ainda.",
    ],
    "suporte": [
        "Já sou cliente e o {p} está travando na emissão de relatórios desde ontem. Preciso de ajuda.",
        "Não consigo acessar minha conta, a senha não funciona. Como resetar?",
        "Bom dia, a nota fiscal do mês passado veio com valor errado. Com quem falo?",
        "O módulo do {p} parou de sincronizar após a atualização. Abrimos chamado mas ninguém respondeu.",
        "Somos clientes há 2 anos e precisamos de treinamento para novos usuários do {p}.",
        "Quero cancelar a renovação automática do contrato.",
    ],
    "spam": [
        "Oferecemos serviços de SEO e marketing digital com 50% de desconto. Responda para saber mais!",
        "Parabéns! Você foi selecionado para receber um prêmio. Clique no link para resgatar.",
        "teste teste 123",
        "Sou estudante e estou fazendo TCC, poderiam responder um questionário?",
        "asdfgh",
        "Trabalhamos com outsourcing de desenvolvedores, gostaria de apresentar nossa empresa.",
    ],
}
# pegadinhas planejadas para o momento "uau" da IA
PEGADINHAS = [
    ("compra imediata", "Oi, tudo bem? Achei o site bem bonito rs. Enfim, precisamos de umas 200 licenças do Atlas Gestão até dezembro, o board já liberou. Quem me atende?"),
    ("compra imediata", "Não é suporte! Sou cliente do Atlas Fiscal e quero CONTRATAR também o Atlas BI para mais 80 usuários neste trimestre."),
    ("suporte", "Gostaria de comprar uma solução que resolva o erro 500 que o Atlas Gestão de vocês está dando aqui desde segunda."),
    ("pesquisa", "Urgente!!! Preciso saber se vocês têm material sobre o Atlas BI para um trabalho da pós."),
    ("spam", "COMPRE AGORA licenças de software com 90% de desconto, revendemos qualquer marca. Chame no WhatsApp."),
]
# lift de conversão por intenção (histórico coerente para o modelo de score)
P_GANHA = {"compra imediata": 0.45, "pesquisa": 0.10, "suporte": 0.03, "spam": 0.0}


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return "".join(c for c in s if c.isalnum())


def fmt_cnpj(c):
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def sql(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def msg_aleatoria():
    intent = rnd.choices(list(MSGS), weights=[25, 40, 20, 15])[0]
    t = rnd.choice(MSGS[intent]).format(p=rnd.choice(PRODUTOS)[1], n=rnd.choice([10, 25, 40, 60, 120, 300]),
                                         v=rnd.choice([50, 80, 150, 300]))
    return intent, t


# ---------------------------------------------------------------- pessoas/leads
def nova_pessoa(i):
    nome = f"{rnd.choice(NOMES)} {rnd.choice(SOBRENOMES)}"
    r = rnd.random()
    if r < 0.70:
        emp, cnpj, uf = rnd.choice(EMPRESAS)
    elif r < 0.85:
        emp, cnpj, uf = None, None, rnd.choice(["SP", "RJ", "MG", "RN", "PE", "PR"])  # sem empresa
    else:
        emp, cnpj, uf = f"{rnd.choice(['Comercial', 'Distribuidora', 'Grupo', 'Indústrias'])} {rnd.choice(SOBRENOMES)}", rnd.choice(CNPJ_INVALIDOS), rnd.choice(["SP", "BA", "RN", "GO"])
    dominio = (slug(emp) if emp else rnd.choice(["gmail", "hotmail", "outlook"])) + ".example.com"
    email = f"{slug(nome.split()[0])}.{slug(nome.split()[1])}{i}@{dominio}"
    tel = f"({rnd.randint(11, 99)}) 9{rnd.randint(1000, 9999)}-{rnd.randint(1000, 9999)}"
    return dict(nome=nome, email=email, empresa=emp, cnpj=cnpj, uf=uf, telefone=tel,
                cargo=rnd.choice(CARGOS) if emp else None)


def main():
    (BASE / "supabase").mkdir(exist_ok=True)
    (BASE / "storage/formularios/carga_inicial").mkdir(parents=True, exist_ok=True)
    (BASE / "storage/formularios/incremental").mkdir(parents=True, exist_ok=True)
    (BASE / "gabarito").mkdir(exist_ok=True)

    # ---------- CRM
    N_LEADS = 320
    leads, opps, inter = [], [], []
    oid = iid = 1
    for i in range(1, N_LEADS + 1):
        p = nova_pessoa(i)
        intent, _ = msg_aleatoria()
        dias = rnd.randint(1, 45) if rnd.random() < 0.35 else rnd.randint(46, 365)
        if dias > 45:   # histórico: já foi trabalhado
            status = "descartado" if intent == "spam" else rnd.choice(["contatado", "qualificado", "descartado"])
        else:
            status = rnd.choices(["novo", "contatado", "qualificado"], [5, 3, 2])[0]
        vend = rnd.choice(VENDEDORES)[0] if status != "novo" or rnd.random() < 0.3 else None
        cnpj_out = p["cnpj"]
        if cnpj_out and rnd.random() < 0.4:      # metade formatada, metade só dígitos -> limpeza na Silver
            cnpj_out = fmt_cnpj(cnpj_out)
        leads.append(dict(id=i, **{**p, "cnpj": cnpj_out}, origem=rnd.choice(ORIGENS), dias=dias,
                          status=status, vendedor_id=vend, _intent=intent))
        if status in ("contatado", "qualificado") and vend:
            for _ in range(rnd.randint(1, 4)):
                inter.append((iid, i, vend, rnd.choice(["ligacao", "email", "reuniao", "whatsapp"]),
                              rnd.randint(0, dias), rnd.choice(["sem resposta", "retornar depois", "interessado", "pediu proposta", "sem interesse"])))
                iid += 1
        if status == "qualificado" or (status == "contatado" and rnd.random() < 0.3):
            prod = rnd.choice(PRODUTOS)
            if dias > 45:
                estagio = "ganha" if rnd.random() < P_GANHA[intent] + (0.1 if status == "qualificado" else 0) else "perdida"
            else:
                estagio = rnd.choice(["prospeccao", "proposta", "negociacao"])
            valor = round(prod[3] * rnd.choice([5, 10, 20, 40, 80]) * rnd.uniform(0.85, 1.1), 2)
            motivo = rnd.choice(["preço", "escolheu concorrente", "sem orçamento", "projeto adiado", "sem retorno"]) if estagio == "perdida" else None
            fech = rnd.randint(0, max(dias - 20, 1)) if estagio in ("ganha", "perdida") else None
            opps.append((oid, i, prod[0], valor, estagio, rnd.randint(max(fech or 0, 0), dias), fech, motivo))
            oid += 1

    s = []
    s.append("-- =====================================================================\n"
             "-- 02_seed.sql  |  Carga do CRM (Atlas Software) - workshop Databricks + IA\n"
             "-- Datas relativas a now(): rode de novo e o dado volta 'fresco'.\n"
             "-- Idempotente: limpa e recarrega tudo (use para resetar entre ensaios).\n"
             "-- =====================================================================\n"
             "BEGIN;\nTRUNCATE crm.interacoes, crm.oportunidades, crm.leads, crm.produtos, crm.vendedores RESTART IDENTITY CASCADE;\n")
    s.append("INSERT INTO crm.vendedores (id, nome, email, regiao, segmento_foco) VALUES\n" + ",\n".join(
        f"  ({v[0]}, {sql(v[1])}, {sql(slug(v[1].split()[0]) + '.' + slug(v[1].split()[1]) + '@atlas.example.com')}, {sql(v[2])}, {sql(v[3])})" for v in VENDEDORES) + ";\n")
    s.append("INSERT INTO crm.produtos (id, nome, categoria, preco_mensal) VALUES\n" + ",\n".join(
        f"  ({p[0]}, {sql(p[1])}, {sql(p[2])}, {p[3]})" for p in PRODUTOS) + ";\n")
    rows = []
    for l in leads:
        h = rnd.randint(8, 19)
        rows.append(f"  ({l['id']}, {sql(l['nome'])}, {sql(l['email'])}, {sql(l['telefone'])}, {sql(l['cargo'])}, "
                    f"{sql(l['empresa'])}, {sql(l['cnpj'])}, {sql(l['uf'])}, {sql(l['origem'])}, {sql(l['status'])}, "
                    f"{sql(l['vendedor_id'])}, now() - interval '{l['dias']} days {h} hours')")
    s.append("INSERT INTO crm.leads (id, nome_contato, email, telefone, cargo, empresa, cnpj, uf, origem, status, vendedor_id, criado_em) VALUES\n"
             + ",\n".join(rows) + ";\n")
    s.append("INSERT INTO crm.oportunidades (id, lead_id, produto_id, valor_estimado, estagio, criada_em, fechada_em, motivo_perda) VALUES\n" + ",\n".join(
        f"  ({o[0]}, {o[1]}, {o[2]}, {o[3]}, {sql(o[4])}, now() - interval '{o[5]} days', "
        f"{'NULL' if o[6] is None else f'now() - interval {chr(39)}{o[6]} days{chr(39)}'}, {sql(o[7])})" for o in opps) + ";\n")
    s.append("INSERT INTO crm.interacoes (id, lead_id, vendedor_id, tipo, ocorrida_em, resultado) VALUES\n" + ",\n".join(
        f"  ({t[0]}, {t[1]}, {t[2]}, {sql(t[3])}, now() - interval '{t[4]} days', {sql(t[5])})" for t in inter) + ";\n")
    s.append("-- realinha as sequences após inserts com id explícito\nDO $$ BEGIN\n"
             + "".join(f"  PERFORM setval(pg_get_serial_sequence('crm.{t}','id'), (SELECT max(id) FROM crm.{t}));\n"
                       for t in ["vendedores", "produtos", "leads", "oportunidades", "interacoes"]) + "END $$;\n"
             + "-- atualizado_em coerente com a criação (o trigger marcaria tudo como 'agora')\n"
               "ALTER TABLE crm.leads DISABLE TRIGGER trg_leads_atualizado_em;\n"
               "UPDATE crm.leads SET atualizado_em = criado_em + interval '2 days' * random();\n"
               "UPDATE crm.leads SET atualizado_em = now() WHERE atualizado_em > now();\n"
               "ALTER TABLE crm.leads ENABLE TRIGGER trg_leads_atualizado_em;\nCOMMIT;\n")
    (BASE / "supabase/02_seed.sql").write_text("\n".join(s), encoding="utf-8")

    # ---------- formulários (JSON Lines no Storage)
    gab = []
    def form(fid, pessoa, intent, texto, quando, canal):
        cnpj = pessoa["cnpj"]
        if cnpj and rnd.random() < 0.5:
            cnpj = fmt_cnpj(cnpj)
        email = pessoa["email"]
        r = {"form_id": fid, "recebido_em": quando.isoformat(timespec="seconds"), "canal": canal,
             "nome": pessoa["nome"], "email": email, "telefone": pessoa["telefone"],
             "empresa": pessoa["empresa"], "cnpj": cnpj,
             "produto_interesse": rnd.choice([None, rnd.choice(PRODUTOS)[1]]), "mensagem": texto,
             "utm": {"source": rnd.choice(["google", "linkedin", "instagram", "direto", "evento"]),
                     "campaign": rnd.choice(["bf2026", "erp-q4", "bi-webinar", None])}}
        gab.append((fid, intent, texto))
        return r

    iniciais, fid = [], 1
    for k in range(150):
        quando = REF - timedelta(days=rnd.randint(1, 30), hours=rnd.randint(0, 10), minutes=rnd.randint(0, 59))
        if rnd.random() < 0.25:   # lead que JÁ existe no CRM -> deduplicação por e-mail na Silver
            l = rnd.choice(leads)
            pessoa = {kk: l[kk] for kk in ("nome", "email", "telefone", "empresa", "uf", "cargo")}
            pessoa["cnpj"] = (l["cnpj"] or "").replace(".", "").replace("/", "").replace("-", "") or None
            if rnd.random() < 0.5:
                pessoa["email"] = "  " + pessoa["email"].upper() + " "  # mesmo e-mail, sujo
        else:
            pessoa = nova_pessoa(1000 + k)
        intent, texto = msg_aleatoria()
        iniciais.append(form(f"F{fid:05d}", pessoa, intent, texto, quando, rnd.choice(["site", "landing_page", "evento"])))
        fid += 1
    # duplicata exata (mesmo envio 2x - duplo clique no botão)
    dup = dict(iniciais[7]); dup["form_id"] = f"F{fid:05d}"; iniciais.append(dup)
    gab.append((dup["form_id"], [g for g in gab if g[0] == iniciais[7]["form_id"]][0][1], dup["mensagem"])); fid += 1
    iniciais.sort(key=lambda r: r["recebido_em"])
    dia_arquivo = REF.strftime("%Y%m%d")
    with open(BASE / f"storage/formularios/carga_inicial/formularios_{dia_arquivo}.jsonl", "w", encoding="utf-8") as f:
        for r in iniciais:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    lote = []
    for intent, texto in PEGADINHAS:
        lote.append(form(f"F{fid:05d}", nova_pessoa(5000 + fid), intent, texto, REF - timedelta(minutes=rnd.randint(5, 50)), "site")); fid += 1
    for _ in range(15):
        intent, texto = msg_aleatoria()
        lote.append(form(f"F{fid:05d}", nova_pessoa(5000 + fid), intent, texto, REF - timedelta(minutes=rnd.randint(5, 120)), rnd.choice(["site", "landing_page"]))); fid += 1
    rnd.shuffle(lote)
    with open(BASE / "storage/formularios/incremental/formularios_lote_ao_vivo.jsonl", "w", encoding="utf-8") as f:
        for r in lote:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(BASE / "gabarito/intencao_formularios.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["form_id", "intencao_real", "mensagem"]); w.writerows(gab)

    # ---------- leads inseridos ao vivo no banco
    vivo = ["-- =====================================================================\n"
            "-- 03_novos_leads_ao_vivo.sql  |  rode DURANTE a demo (bloco Ingestão)\n"
            "-- Insere 5 leads 'agora' para mostrar a carga incremental por atualizado_em.\n"
            "-- =====================================================================\n"
            "INSERT INTO crm.leads (nome_contato, email, telefone, cargo, empresa, cnpj, uf, origem, status) VALUES"]
    vr = []
    for k in range(5):
        p = nova_pessoa(9000 + k)
        vr.append(f"  ({sql(p['nome'])}, {sql(p['email'])}, {sql(p['telefone'])}, {sql(p['cargo'])}, {sql(p['empresa'])}, {sql(p['cnpj'])}, {sql(p['uf'])}, 'evento', 'novo')")
    vivo.append(",\n".join(vr) + ";\n\nSELECT id, nome_contato, empresa, criado_em FROM crm.leads ORDER BY id DESC LIMIT 5;\n")
    (BASE / "supabase/03_novos_leads_ao_vivo.sql").write_text("\n".join(vivo), encoding="utf-8")

    print(f"leads={len(leads)} oportunidades={len(opps)} interacoes={len(inter)} "
          f"forms_iniciais={len(iniciais)} forms_lote={len(lote)} ref={REF.date()}")


if __name__ == "__main__":
    main()
