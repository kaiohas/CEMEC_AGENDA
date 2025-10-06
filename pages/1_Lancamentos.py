import streamlit as st
import pandas as pd
from datetime import date
from supabase_client import client
from auth import require_roles
from utils import listar_variaveis_por_grupo

st.set_page_config(page_title="Lançamentos | Agenda Unificada", page_icon="🗓️", layout="wide")
require_roles(["agenda", "gerencia"])
user = st.session_state["user"]

st.title("🗓️ Lançamentos de Agendamentos")

def calc_programacao(data_cad: date, data_visita: date, foi_remarcado: bool = False) -> str:
    if not (data_cad and data_visita):
        return None
    delta = (data_visita - data_cad).days
    horas = (pd.Timestamp(data_visita) - pd.Timestamp(data_cad)).total_seconds() / 3600.0
    if horas < 24:
        return "Não Programada"
    if delta > 15:
        return "Programada"
    if delta > 7:
        return "Incluída"
    return "Extraordinário"

# Combos (ag_variaveis)
op_estudo       = listar_variaveis_por_grupo("Estudo")
op_reembolso    = listar_variaveis_por_grupo("Reembolso")
op_tipo_visita  = listar_variaveis_por_grupo("Tipo_visita")
op_medico       = listar_variaveis_por_grupo("Medico_responsavel")
op_consultorio  = listar_variaveis_por_grupo("Consultorio")
op_jejum        = listar_variaveis_por_grupo("Jejum")

st.subheader("Novo agendamento")
with st.form("frm_novo_agendamento", clear_on_submit=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        data_visita   = st.date_input("Data da visita")
        id_paciente   = st.text_input("ID Paciente")
        nome_paciente = st.text_input("Nome do paciente")
    with c2:
        estudo = st.selectbox("Estudo", options=[{"id": None, "nome_variavel": "(selecione)"}] + op_estudo, format_func=lambda x: x["nome_variavel"])
        tipo_visita = st.selectbox("Tipo de visita", options=[{"id": None, "nome_variavel": "(selecione)"}] + op_tipo_visita, format_func=lambda x: x["nome_variavel"])
        reembolso = st.selectbox("Reembolso", options=[{"id": None, "nome_variavel": "(selecione)"}] + op_reembolso, format_func=lambda x: x["nome_variavel"])
    with c3:
        medico_resp = st.selectbox("Médico responsável", options=[{"id": None, "nome_variavel": "(selecione)"}] + op_medico, format_func=lambda x: x["nome_variavel"])
        consultorio = st.selectbox("Consultório", options=[{"id": None, "nome_variavel": "(selecione)"}] + op_consultorio, format_func=lambda x: x["nome_variavel"])
        jejum = st.selectbox("Jejum", options=[{"id": None, "nome_variavel": "(selecione)"}] + op_jejum, format_func=lambda x: x["nome_variavel"])

    c4, c5, c6 = st.columns(3)
    with c4:
        hora_consulta = st.time_input("Hora da consulta", value=None)
        horario_uber  = st.time_input("Horário do Uber", value=None)
    with c5:
        visita     = st.text_input("Visita")
        obs_visita = st.text_input("Obs. da visita")
    with c6:
        obs_coleta = st.text_input("Obs. de coleta")

    submitted = st.form_submit_button("Cadastrar agendamento", use_container_width=True, type="primary")

if submitted:
    if not data_visita or not nome_paciente.strip():
        st.warning("Preencha ao menos **Data da visita** e **Nome do paciente**.")
    else:
        data_cadastro = date.today()
        programacao = calc_programacao(data_cadastro, data_visita)

        payload = {
            "data_cadastro": str(data_cadastro),
            "responsavel_agendamento_id": user["id"],
            "responsavel_agendamento_nome": user["username"],

            "data_visita": str(data_visita),
            "estudo_id": estudo["id"] if estudo and estudo.get("id") else None,
            "id_paciente": id_paciente.strip() if id_paciente else None,
            "nome_paciente": nome_paciente.strip(),
            "hora_consulta": str(hora_consulta) if hora_consulta else None,
            "horario_uber": str(horario_uber) if horario_uber else None,

            "reembolso_id": reembolso["id"] if reembolso and reembolso.get("id") else None,
            "visita": visita.strip() if visita else None,
            "tipo_visita_id": tipo_visita["id"] if tipo_visita and tipo_visita.get("id") else None,
            "medico_responsavel_id": medico_resp["id"] if medico_resp and medico_resp.get("id") else None,
            "consultorio_id": consultorio["id"] if consultorio and consultorio.get("id") else None,
            "obs_visita": obs_visita.strip() if obs_visita else None,
            "jejum_id": jejum["id"] if jejum and jejum.get("id") else None,
            "obs_coleta": obs_coleta.strip() if obs_coleta else None,

            "programacao": programacao,
        }

        resp = client.table("ag_agendamentos").insert(payload).execute()
        if resp.data:
            st.success("Agendamento cadastrado com sucesso.")
            st.rerun()
        else:
            st.error("Falha ao cadastrar. Verifique os campos obrigatórios.")

st.divider()

# ----------------- Listagem -----------------
st.subheader("Agendamentos cadastrados")

lc1, lc2 = st.columns(2)
with lc1:
    flt_data = st.date_input("Filtrar por data de visita", value=None, key="flt_dt_list")
with lc2:
    flt_nome = st.text_input("Filtrar por nome (contém)", key="flt_nm_list")

q = client.table("ag_agendamentos").select(
    "id, data_visita, nome_paciente, id_paciente, estudo_id, "
    "hora_consulta, horario_uber, reembolso_id, "
    "visita, tipo_visita_id, medico_responsavel_id, consultorio_id, "
    "obs_visita, jejum_id, obs_coleta, programacao, "
    "hora_chegada, hora_saida, responsavel_agendamento_nome"
)

if flt_data:
    q = q.eq("data_visita", str(flt_data))
if flt_nome:
    q = q.ilike("nome_paciente", f"%{flt_nome}%")

rows = q.order("data_visita", desc=True).order("hora_consulta").limit(1000).execute().data or []
df = pd.DataFrame(rows)

def _map_dict(grupo):
    lst = listar_variaveis_por_grupo(grupo) or []
    return {x["id"]: x["nome_variavel"] for x in lst}

map_estudo      = _map_dict("Estudo")
map_reembolso   = _map_dict("Reembolso")
map_tipo        = _map_dict("Tipo_visita")
map_medico      = _map_dict("Medico_responsavel")
map_consultorio = _map_dict("Consultorio")
map_jejum       = _map_dict("Jejum")

if not df.empty:
    df["estudo"]             = df["estudo_id"].map(map_estudo)
    df["reembolso"]          = df["reembolso_id"].map(map_reembolso)
    df["tipo_visita"]        = df["tipo_visita_id"].map(map_tipo)
    df["medico_responsavel"] = df["medico_responsavel_id"].map(map_medico)
    df["consultorio"]        = df["consultorio_id"].map(map_consultorio)
    df["jejum"]              = df["jejum_id"].map(map_jejum)

    # Formatação de hora_chegada / hora_saida
    if "hora_chegada" in df.columns:
        df["hora_chegada"] = (
            pd.to_datetime(df["hora_chegada"], errors="coerce", utc=True)
            .dt.tz_convert("America/Sao_Paulo")
            .dt.strftime("%d/%m/%Y %H:%M:%S")
        )
    if "hora_saida" in df.columns:
        df["hora_saida"] = (
            pd.to_datetime(df["hora_saida"], errors="coerce", utc=True)
            .dt.tz_convert("America/Sao_Paulo")
            .dt.strftime("%d/%m/%Y %H:%M:%S")
        )

    cols_show = [
        "id", "data_visita", "hora_consulta",
        "id_paciente", "nome_paciente",
        "estudo", "programacao",
        "horario_uber",
        "reembolso",
        "visita", "tipo_visita", "medico_responsavel", "consultorio",
        "obs_visita", "jejum", "obs_coleta",
        "hora_chegada", "hora_saida",
        "responsavel_agendamento_nome",
    ]
    cols_show = [c for c in cols_show if c in df.columns]
    st.dataframe(df[cols_show], use_container_width=True, hide_index=True)
else:
    st.info("Ainda não há agendamentos cadastrados para os filtros aplicados.")
