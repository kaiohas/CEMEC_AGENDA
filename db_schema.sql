-- Criação do esquema básico para a Agenda Unificada
-- Observação: usamos nomes de colunas em snake_case para evitar problemas de aspas.
-- A UI exibirá rótulos com acentos normalmente.


create table if not exists ag_users (
    id bigserial primary key,
    username text unique not null,
    password_hash text not null,
    role text not null check (role in ('agenda','gestao','gerencia')),
    is_active boolean not null default true,
    linked_agenda_user_id bigint null references users(id) on delete set null,
    created_at timestamptz not null default now()
);


create table if not exists ag_variaveis (
    id bigserial primary key,
    grupo_variavel text not null,
    nome_variavel text not null,
    is_active boolean not null default true,
    unique (grupo_variavel, nome_variavel)
);


-- Tabela de tipos de status por etapa (para popular os selects da tela de Gestão)
create table if not exists ag_status_tipos (
    id bigserial primary key,
    nome_etapa text not null, -- ex: 'status_medico', 'status_enfermagem', ...
    nome_status text not null,
    unique (nome_etapa, nome_status)
);


create table if not exists ag_agendamentos (
    id bigserial primary key,
    data_cadastro timestamptz not null default now(),
    responsavel_agendamento_id bigint not null references users(id),
    responsavel_agendamento_nome text not null,
    data_visita date not null,
    estudo_id bigint references variaveis(id),
    id_paciente text,
    nome_paciente text,
    hora_consulta time,
    programacao text, -- calculada na aplicação
    horario_uber time,
    reembolso_id bigint references variaveis(id),
    valor_financeiro numeric(12,2),
    visita text,
    tipo_visita_id bigint references variaveis(id),
    medico_responsavel_id bigint references variaveis(id),
    consultorio_id bigint references variaveis(id),
    obs_visita text,
    jejum_id bigint references variaveis(id),
    obs_coleta text,
    hora_chegada timestamptz,
    desfecho_atendimento_id bigint references variaveis(id),
    hora_saida timestamptz
);


-- Log de status por etapa
create table if not exists ag_log_agendamentos (
    id bigserial primary key,
    agendamento_id bigint not null references agendamentos(id) on delete cascade,
    nome_etapa text not null, -- mesma convenção de status_tipos.nome_etapa
    status_etapa text not null, -- valor escolhido
    data_hora_etapa timestamptz not null default now(),
    usuario_alteracao_id bigint not null references users(id),
    usuario_alteracao_nome text not null
);


-- Índices úteis
create index if not exists idx_agend_data_visita on ag_agendamentos (data_visita);
create index if not exists idx_agend_resp on ag_agendamentos (responsavel_agendamento_id);
create index if not exists idx_log_agendamento on ag_log_agendamentos (agendamento_id);
create index if not exists idx_log_data on ag_log_agendamentos (data_hora_etapa);


-- Seeds opcionais (básicos) para variáveis
insert into ag_variaveis (grupo_variavel, nome_variavel) values
    ('Estudo','ESTUDO A'),('Estudo','ESTUDO B'),
    ('Reembolso','Sim'),('Reembolso','Não'),
    ('Tipo_visita','Primeira consulta'),('Tipo_visita','Retorno'),
    ('Medico_responsavel','Dr. Silva'),('Medico_responsavel','Dra. Souza'),
    ('Consultorio','Sala 1'),('Consultorio','Sala 2'),
    ('Jejum','Sim'),('Jejum','Não'),
    ('Desfecho_atendimento','Concluído'),('Desfecho_atendimento','Cancelado')
on conflict do nothing;