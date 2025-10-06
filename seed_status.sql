-- Semeia tipos de status por etapa
-- Etapas: status_medico, status_enfermagem, status_farmacia, status_espirometria,
-- status_nutricionista, status_coordenacao, status_recepcao


insert into ag_status_tipos (nome_etapa, nome_status) values
('status_medico','Aguardando'),('status_medico','Em atendimento'),('status_medico','Concluído'),('status_medico','Cancelado'),
('status_enfermagem','Aguardando'),('status_enfermagem','Em atendimento'),('status_enfermagem','Concluído'),('status_enfermagem','Cancelado'),
('status_farmacia','Aguardando'),('status_farmacia','Em atendimento'),('status_farmacia','Concluído'),('status_farmacia','Cancelado'),
('status_espirometria','Aguardando'),('status_espirometria','Em atendimento'),('status_espirometria','Concluído'),('status_espirometria','Cancelado'),
('status_nutricionista','Aguardando'),('status_nutricionista','Em atendimento'),('status_nutricionista','Concluído'),('status_nutricionista','Cancelado'),
('status_coordenacao','Aguardando'),('status_coordenacao','Em atendimento'),('status_coordenacao','Concluído'),('status_coordenacao','Cancelado'),
('status_recepcao','Aguardando'),('status_recepcao','Em atendimento'),('status_recepcao','Concluído'),('status_recepcao','Cancelado')
on conflict do nothing;