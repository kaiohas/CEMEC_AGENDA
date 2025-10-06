import streamlit as st
from auth import login, logout


st.set_page_config(page_title="Agenda Unificada", page_icon="📅", layout="wide")


st.title("📅 Agenda Unificada CEMEC")


if "user" not in st.session_state:
    st.subheader("Login")
    with st.form("login_form"):
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("Usuário", key="username")
        with col2:
            password = st.text_input("Senha", type="password", key="password")
        ok = st.form_submit_button("Entrar")
    if ok:
        user = login(username, password)
        if user:
            st.success(f"Bem-vindo(a), {user['username']}! Use o menu 'Pages' à esquerda.")
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos, ou usuário inativo.")
else:
    user = st.session_state["user"]
    st.info(f"Logado como: **{user['username']}** | Perfil: **{user['role']}**")
    st.page_link("app.py", label="🏠 Início", icon="🏠")
    st.page_link("pages/1_Lancamentos.py", label="📝 Lançamentos")
    st.page_link("pages/2_Gestao.py", label="🧭 Gestão")
    st.page_link("pages/3_Variaveis.py", label="⚙️ Variáveis (gerência)")
    st.page_link("pages/4_Usuarios.py", label="👥 Usuários (gerência)")


st.write("\n")
st.markdown(
    "#### Como usar\n"
        "- **Agenda**: usa a tela *Lançamentos* para cadastrar agendamentos e ver todos os existentes.\n"
        "- **Gestão**: usa a tela *Gestão* para atualizar o status das etapas do agendamento, registrando log.\n"
        "- **Gerência**: tem acesso a todas as telas, pode excluir agendamentos, gerenciar variáveis e usuários.\n"
    )


if st.button("Sair"):
    logout()
    st.rerun()