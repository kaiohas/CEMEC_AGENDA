# 📅 Agenda Unificada — Streamlit + Supabase

Aplicação multipáginas com perfis **agenda**, **gestao** e **gerencia**:
- **Agenda**: cadastrar agendamentos e visualizar todos.
- **Gestão**: alterar status das etapas, registrando log (vê apenas agendamentos do usuário agenda vinculado).
- **Gerência**: tudo acima + gerenciar variáveis, usuários e excluir agendamentos.

## 🚀 Como rodar

1. **Clonar/criar pasta** e salvar os arquivos abaixo mantendo a estrutura:
```
.
├── app.py
├── auth.py
├── supabase_client.py
├── utils.py
├── requirements.txt
├── .env.example  (copiar para .env)
├── db_schema.sql
├── seed_status.sql
└── pages
    ├── 1_Lancamentos.py
    ├── 2_Gestao.py
    ├── 3_Variaveis.py
    └── 4_Usuarios.py
```

2. **Criar ambiente e instalar dependências**:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

3. **Configurar Supabase**:
   - Crie um projeto no Supabase, pegue **Project URL** e **anon public key**.
   - Copie `.env.example` para `.env` e preencha `SUPABASE_URL` e `SUPABASE_KEY`.
   - No Supabase SQL editor, rode `db_schema.sql` e depois `seed_status.sql`.
   - Opcional: crie um usuário inicial de gerência diretamente no SQL:
```sql
insert into ag_users (username, password_hash, role)
values ('admin', '$2b$12$yD4dZ2o4kN8Yl0wCzR5M5eZxwGg9x6m5Q7J0oG4gYUrS7cC8VgPdi', 'gerencia');
-- senha deste hash (exemplo) = Admin@123  (gere outro hash em produção)
```

4. **Executar**:
```bash
streamlit run app.py
```

## 🧮 Regras de Programação
- **Não Programada**: incluídos com antecedência < 24 horas.
- **Programada**: > 15 dias.
- **Incluída**: > 7 dias.
- **Extraordinário**: entre 24h e 7 dias.
- ("Remanejada" pode ser incorporada futuramente ao editar Data da Visita com antecedência < 7 dias).

## 📝 Observações
- **hora_chegada** é digitada na tela de Gestão.
- **hora_saida** é automaticamente definida como o **último horário** registrado no log de etapas daquele agendamento.
- Para **gestão**, a visibilidade é limitada ao **usuário agenda vinculado** na tela de Usuários.
- As colunas do banco usam snake_case; os rótulos na UI exibem acentuação normalmente.
- Este app usa **autenticação simples** via tabela `users` + `bcrypt`. (Supabase Auth pode ser integrado futuramente se desejar.)

## 🔐 Dicas de produção
- Ative **RLS** no Supabase e crie policies conforme perfis se quiser endurecer segurança no backend.
- Gere **hashes de senha** próprios (não use o de exemplo em produção).
- Crie índices adicionais conforme crescimento do volume.