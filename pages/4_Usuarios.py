import streamlit as st
import pandas as pd
from supabase_client import client
from auth import require_roles, hash_password

st.set_page_config(page_title="Usuários | Agenda Unificada", page_icon="👥", layout="wide")
require_roles(["gerencia"])  # Apenas gerência

st.title("👥 Gestão de Usuários")

aba1, aba2 = st.tabs(["Cadastrar", "Alterar ou excluir"]) 

with aba1:
    st.subheader("Novo usuário")
    col1, col2, col3 = st.columns(3)
    with col1:
        username = st.text_input("Usuário (login)")
        role = st.selectbox("Perfil", ["agenda", "gestao", "gerencia"])
    with col2:
        pwd = st.text_input("Senha", type="password")
        pwd2 = st.text_input("Confirmar senha", type="password")
    with col3:
        linked_id = None
        if role == "gestao":
            ag_users = (
                client.table("ag_users").select("id, username").eq("role", "agenda").eq("is_active", True).order("username").execute().data or []
            )
            opt = st.selectbox("Vincular a usuário 'agenda'", options=[{"id": None, "username": "(nenhum)"}] + ag_users, format_func=lambda x: x["username"])
            linked_id = opt.get("id")
    if st.button("Criar usuário", type="primary"):
        if not username or not pwd:
            st.warning("Informe usuário e senha.")
        elif pwd != pwd2:
            st.warning("As senhas não coincidem.")
        else:
            payload = {
                "username": username.strip(),
                "password_hash": hash_password(pwd),
                "role": role,
                "is_active": True,
                "linked_agenda_user_id": linked_id,
            }
            resp = client.table("ag_users").insert(payload).execute()
            if resp.data:
                st.success("Usuário criado.")
            else:
                st.error("Falha ao criar (talvez usuário já exista).")

with aba2:
    st.subheader("Usuários cadastrados")
    users = (
        client.table("ag_users")
        .select("id, username, role, is_active, linked_agenda_user_id")
        .order("username")
        .execute()
        .data or []
    )
    df = pd.DataFrame(users)
    st.dataframe(df, width="stretch", hide_index=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        uid = st.number_input("ID p/ alternar ativo/inativo", min_value=0, step=1)
        if st.button("Ativar/Inativar"):
            cur = client.table("ag_users").select("is_active").eq("id", int(uid)).maybe_single().execute().data
            if cur is not None:
                client.table("ag_users").update({"is_active": (not cur["is_active"])}).eq("id", int(uid)).execute()
                st.success("Atualizado.")
            else:
                st.warning("ID não encontrado.")
    with c2:
        uid_del = st.number_input("ID p/ excluir", min_value=0, step=1, key="uid_del")
        if st.button("Excluir usuário"):
            client.table("ag_users").delete().eq("id", int(uid_del)).execute()
            st.success("Excluído (se não referenciado).")
    with c3:
        st.info("Exclusão pode falhar por chaves estrangeiras.")
    st.subheader("Atualizar senha")
    col1, col2, col3 = st.columns(3)
    with col1:
        uidp = st.number_input("ID do usuário", min_value=0, step=1)
    with col2:
        newp = st.text_input("Nova senha", type="password")
    with col3:
        newp2 = st.text_input("Confirmar nova senha", type="password")
    if st.button("Atualizar senha"):
        if newp != newp2:
            st.warning("As senhas não coincidem.")
        else:
            client.table("ag_users").update({"password_hash": hash_password(newp)}).eq("id", int(uidp)).execute()
            st.success("Senha atualizada.")