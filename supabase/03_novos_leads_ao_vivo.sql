-- =====================================================================
-- 03_novos_leads_ao_vivo.sql  |  rode DURANTE a demo (bloco Ingestão)
-- Insere 5 leads 'agora' para mostrar a carga incremental por atualizado_em.
-- =====================================================================
INSERT INTO crm.leads (nome_contato, email, telefone, cargo, empresa, cnpj, uf, origem, status) VALUES
  ('Larissa Martins', 'larissa.martins9000@cielo.example.com', '(30) 91418-2740', 'Controller', 'Cielo', '01027058000191', 'SP', 'evento', 'novo'),
  ('Otávio Gomes', 'otavio.gomes9001@embratel.example.com', '(76) 96636-4520', 'Head de Dados', 'Embratel', '33530486000129', 'RJ', 'evento', 'novo'),
  ('Camila Lopes', 'camila.lopes9002@outlook.example.com', '(21) 92266-4679', NULL, NULL, NULL, 'RN', 'evento', 'novo'),
  ('Beatriz Correia', 'beatriz.correia9003@sabesp.example.com', '(64) 99830-2986', 'CIO', 'Sabesp', '43776517000180', 'SP', 'evento', 'novo'),
  ('Daniel Dias', 'daniel.dias9004@suzano.example.com', '(77) 98225-6192', 'CFO', 'Suzano', '16404287000155', 'BA', 'evento', 'novo');

SELECT id, nome_contato, empresa, criado_em FROM crm.leads ORDER BY id DESC LIMIT 5;
