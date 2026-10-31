-- =====================================================================
-- 01_schema.sql  |  CRM da Atlas Software (fictícia) - workshop Databricks + IA
-- Rode no Supabase: Dashboard > SQL Editor > New query > colar > Run
-- Idempotente: pode rodar quantas vezes quiser (recria tudo do zero).
-- Depois rode 02_seed.sql.
-- =====================================================================

DROP SCHEMA IF EXISTS crm CASCADE;
CREATE SCHEMA crm;
COMMENT ON SCHEMA crm IS 'CRM da Atlas Software - fonte relacional do workshop';

CREATE TABLE crm.vendedores (
  id             serial PRIMARY KEY,
  nome           text        NOT NULL,
  email          text        NOT NULL UNIQUE,
  regiao         text        NOT NULL,
  segmento_foco  text        NOT NULL,
  ativo          boolean     NOT NULL DEFAULT true
);

CREATE TABLE crm.produtos (
  id            serial PRIMARY KEY,
  nome          text          NOT NULL,
  categoria     text          NOT NULL,
  preco_mensal  numeric(12,2) NOT NULL   -- preço de lista por licença/mês
);

CREATE TABLE crm.leads (
  id            serial PRIMARY KEY,
  nome_contato  text        NOT NULL,
  email         text        NOT NULL,
  telefone      text,
  cargo         text,
  empresa       text,
  cnpj          text,                   -- propositalmente sujo: com e sem máscara, alguns inválidos
  uf            char(2),
  origem        text        NOT NULL CHECK (origem IN ('site','evento','indicacao','outbound','linkedin')),
  status        text        NOT NULL DEFAULT 'novo' CHECK (status IN ('novo','contatado','qualificado','descartado')),
  vendedor_id   int         REFERENCES crm.vendedores(id),
  criado_em     timestamptz NOT NULL DEFAULT now(),
  atualizado_em timestamptz NOT NULL DEFAULT now()   -- watermark p/ carga incremental
);
CREATE INDEX ix_leads_atualizado_em ON crm.leads (atualizado_em);
CREATE INDEX ix_leads_email ON crm.leads (lower(email));

CREATE TABLE crm.oportunidades (
  id              serial PRIMARY KEY,
  lead_id         int           NOT NULL REFERENCES crm.leads(id),
  produto_id      int           NOT NULL REFERENCES crm.produtos(id),
  valor_estimado  numeric(14,2) NOT NULL,
  estagio         text          NOT NULL CHECK (estagio IN ('prospeccao','proposta','negociacao','ganha','perdida')),
  criada_em       timestamptz   NOT NULL DEFAULT now(),
  fechada_em      timestamptz,
  motivo_perda    text
);

CREATE TABLE crm.interacoes (
  id           serial PRIMARY KEY,
  lead_id      int         NOT NULL REFERENCES crm.leads(id),
  vendedor_id  int         NOT NULL REFERENCES crm.vendedores(id),
  tipo         text        NOT NULL CHECK (tipo IN ('ligacao','email','reuniao','whatsapp')),
  ocorrida_em  timestamptz NOT NULL DEFAULT now(),
  resultado    text
);

-- mantém atualizado_em sempre correto em qualquer UPDATE
CREATE OR REPLACE FUNCTION crm.set_atualizado_em() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.atualizado_em := now(); RETURN NEW; END $$;
CREATE TRIGGER trg_leads_atualizado_em BEFORE UPDATE ON crm.leads
  FOR EACH ROW EXECUTE FUNCTION crm.set_atualizado_em();

-- ---------------------------------------------------------------------
-- Usuário SOMENTE LEITURA para o Databricks (boa prática: não usar o postgres)
-- TROQUE a senha antes de rodar. Pelo Session pooler o usuário fica:
--   databricks_reader.<PROJECT_REF>
-- ---------------------------------------------------------------------
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'databricks_reader') THEN
    CREATE ROLE databricks_reader LOGIN PASSWORD 'TROQUE_ESTA_SENHA';
  END IF;
END $$;
GRANT USAGE ON SCHEMA crm TO databricks_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA crm TO databricks_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA crm GRANT SELECT ON TABLES TO databricks_reader;
