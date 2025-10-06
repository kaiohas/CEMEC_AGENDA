import streamlit as st
import pandas as pd
from supabase_client import client
from auth import require_roles
from utils import GRUPOS_VARIAVEIS

st.set_page_config(page_title="Variáveis | Agenda Unificada", page_icon="⚙️", layout="wide")
require_roles(["gerencia"])

st.title("⚙️ Gestão de Variáveis")

aba1, aba2 = st.tabs(["Variáveis de seleção", "Tipos de status (etapas)"])

# ==============================================
# ABA 1 — Variáveis de seleção
# ==============================================
with aba1:
    st.subheader("Variáveis de seleção (Estudo, Reembolso, etc.)")
    c1, c2 = st.columns([1, 2], gap="large")

    with c1:
        grupo = st.selectbox("Grupo", GRUPOS_VARIAVEIS, key="var_grupo")
        nome = st.text_input("Nome da variável", key="var_nome")

        if st.button("Adicionar variável", use_container_width=True):
            if not nome.strip():
                st.warning("Informe o nome da variável.")
            else:
                resp = client.table("ag_variaveis").insert({
                    "grupo_variavel": grupo,
                    "nome_variavel": nome.strip(),
                    "is_active": True,
                }).execute()
                if resp.data:
                    st.success("Variável adicionada.")
                    st.rerun()
                else:
                    st.error("Falha ao adicionar (talvez já exista).")

    with c2:
        # Consulta já filtrando pelo grupo escolhido
        dados = (
            client.table("ag_variaveis")
            .select("id, grupo_variavel, nome_variavel, is_active")
            .eq("grupo_variavel", grupo)
            .order("nome_variavel")
            .execute()
            .data or []
        )
        df = pd.DataFrame(dados)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Mostrando apenas variáveis do grupo **{grupo}**")

        colA, colB = st.columns(2)
        with colA:
            vid = st.number_input("ID para alternar ativo/inativo", min_value=0, step=1, key="var_toggle_id")
            if st.button("Alternar ativo/inativo"):
                cur = client.table("ag_variaveis").select("is_active").eq("id", int(vid)).maybe_single().execute().data
                if cur is not None:
                    newv = not cur["is_active"]
                    client.table("ag_variaveis").update({"is_active": newv}).eq("id", int(vid)).execute()
                    st.success("Atualizado.")
                    st.rerun()
                else:
                    st.warning("ID não encontrado.")
        with colB:
            delid = st.number_input("ID para excluir", min_value=0, step=1, key="var_del_id")
            if st.button("Excluir variável"):
                client.table("ag_variaveis").delete().eq("id", int(delid)).execute()
                st.success("Excluída (se não referenciada).")
                st.rerun()

# ==============================================
# ABA 2 — Tipos de status por etapa
# ==============================================
with aba2:
    st.subheader("Tipos de status por etapa")
    col1, col2 = st.columns([1, 2], gap="large")

    with col1:
        etapa = st.selectbox("Etapa", [
            "status_medico",
            "status_enfermagem",
            "status_farmacia",
            "status_espirometria",
            "status_nutricionista",
            "status_coordenacao",
            "status_recepcao",
        ], key="status_etapa")

        nome_status = st.text_input("Nome do status", key="status_nome")

        if st.button("Adicionar status", use_container_width=True):
            if not nome_status.strip():
                st.warning("Informe o nome do status.")
            else:
                resp = client.table("ag_status_tipos").insert({
                    "nome_etapa": etapa,
                    "nome_status": nome_status.strip(),
                }).execute()
                if resp.data:
                    st.success("Status adicionado.")
                    st.rerun()
                else:
                    st.error("Falha ao adicionar (talvez já exista).")

    with col2:
        # Consulta já filtrando pela etapa escolhida
        dados2 = (
            client.table("ag_status_tipos")
            .select("id, nome_etapa, nome_status")
            .eq("nome_etapa", etapa)
            .order("nome_status")
            .execute()
            .data or []
        )
        df2 = pd.DataFrame(dados2)
        st.dataframe(df2, use_container_width=True, hide_index=True)
        st.caption(f"Mostrando apenas status da etapa **{etapa}**")

        did = st.number_input("ID para excluir", min_value=0, step=1, key="status_del_id")
        if st.button("Excluir status"):
            client.table("ag_status_tipos").delete().eq("id", int(did)).execute()
            st.success("Status excluído.")
            st.rerun()
