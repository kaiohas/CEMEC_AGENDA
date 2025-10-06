import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from supabase_client import client
from auth import require_roles
from utils import (
    ETAPAS,
    listar_status_da_etapa,
    status_atual_por_etapa,
    atualizar_hora_saida,
    listar_variaveis_por_grupo,
)

st.set_page_config(page_title="Gestão | Agenda Unificada", page_icon="🧭", layout="wide")
require_roles(["gestao", "gerencia"])
user = st.session_state["user"]

st.title("🧭 Gestão de Agendamentos")

# -------------------- Filtros globais --------------------
fc1, fc2, fc3, fc4, fc5 = st.columns(5)
with fc1:
    dt_ini = st.date_input("Data visita (início)")
with fc2:
    dt_fim = st.date_input("Data visita (fim)")
with fc3:
    termo_paciente = st.text_input("Paciente (nome ou ID contém)")
with fc4:
    estudos = listar_variaveis_por_grupo("Estudo") or []
    map_estudo = {e["id"]: e["nome_variavel"] for e in estudos}
    est_sel = st.selectbox(
        "Estudo",
        options=[{"id": None, "nome_variavel": "(todos)"}] + estudos,
        format_func=lambda x: x["nome_variavel"],
        index=0,
        key="flt_estudo",
    )
with fc5:
    resp_sel = None  # preenchido depois com o universo visível

# Também vamos precisar do texto de Tipo de Visita para rótulos e relatório
tipos_visita_list = listar_variaveis_por_grupo("Tipo_visita") or []
map_tipo_visita = {t["id"]: t["nome_variavel"] for t in tipos_visita_list}

def query_escopo_base():
    q = client.table("ag_agendamentos").select(
        "id, responsavel_agendamento_id, responsavel_agendamento_nome, estudo_id, "
        "data_visita, nome_paciente, id_paciente, hora_consulta, programacao, hora_chegada, hora_saida, "
        "tipo_visita_id, visita"
    )
    if user["role"] == "gestao":
        linked = user.get("linked_agenda_user")
        if not linked:
            st.error("Seu usuário de gestão não está vinculado a um usuário agenda. Solicite à gerência.")
            st.stop()
        q = q.eq("responsavel_agendamento_id", linked["id"])
    return q

# Universo base para montar combo de responsáveis
base_universe = query_escopo_base().limit(5000).execute().data or []
df_universe = pd.DataFrame(base_universe)

with fc5:
    if not df_universe.empty:
        df_resps = (
            df_universe[["responsavel_agendamento_id", "responsavel_agendamento_nome"]]
            .drop_duplicates()
            .sort_values("responsavel_agendamento_nome")
        )
        resp_opts = [{"id": None, "nome": "(todos)"}] + [
            {"id": int(r["responsavel_agendamento_id"]), "nome": r["responsavel_agendamento_nome"]}
            for _, r in df_resps.iterrows()
        ]
    else:
        resp_opts = [{"id": None, "nome": "(todos)"}]
    resp_sel = st.selectbox("Responsável", options=resp_opts, format_func=lambda x: x["nome"])

def base_query_agendamentos():
    q = client.table("ag_agendamentos").select("*")
    if user["role"] == "gestao":
        linked = user.get("linked_agenda_user")
        if not linked:
            st.error("Seu usuário de gestão não está vinculado a um usuário agenda. Solicite à gerência.")
            st.stop()
        q = q.eq("responsavel_agendamento_id", linked["id"])
    if dt_ini:
        q = q.gte("data_visita", str(dt_ini))
    if dt_fim:
        q = q.lte("data_visita", str(dt_fim))
    if termo_paciente:
        q = q.or_(f"nome_paciente.ilike.%{termo_paciente}%,id_paciente.ilike.%{termo_paciente}%")
    if est_sel and est_sel["id"] is not None:
        q = q.eq("estudo_id", est_sel["id"])
    if resp_sel and resp_sel["id"] is not None:
        q = q.eq("responsavel_agendamento_id", resp_sel["id"])
    return q.order("data_visita").order("hora_consulta").limit(1000)

agends = base_query_agendamentos().execute().data or []
if not agends:
    st.info("Sem agendamentos para os filtros/escopo.")
    st.stop()

# ---------- Helpers de formatação ----------
def _fmt_time_hhmmss(ts):
    if not ts:
        return "--:--:--"
    t = pd.to_datetime(ts, errors="coerce", utc=True)
    if pd.isna(t):
        return "--:--:--"
    return t.tz_convert("America/Sao_Paulo").strftime("%H:%M:%S")

def _fmt_dt_ddmmyyyy_hhmmss(ts, assume_utc=False):
    if not ts:
        return ""
    if assume_utc:
        t = pd.to_datetime(ts, errors="coerce", utc=True)
        if pd.isna(t):
            return ""
        return t.tz_convert("America/Sao_Paulo").strftime("%d/%m/%Y %H:%M:%S")
    else:
        t = pd.to_datetime(ts, errors="coerce")
        if pd.isna(t):
            return ""
        return t.strftime("%d/%m/%Y %H:%M:%S")

# -------------------- Abas --------------------
aba_gestao, aba_rel, aba_edit = st.tabs(["Gestão", "Relatório", "Edição (Gerência)"])

# =======================================================================================
# ABA 1 — GESTÃO
# =======================================================================================
with aba_gestao:
    # Label com: Estudo, Programação, Tipo de visita (texto) e Visita
    def _fmt_opt(a):
        hc = a.get("hora_consulta") or "--:--:--"
        est_txt = map_estudo.get(a.get("estudo_id"), "(sem estudo)")
        tipo_txt = map_tipo_visita.get(a.get("tipo_visita_id"), "(s/ tipo)")
        visita = a.get("visita") or "(s/ visita)"
        prog = a.get("programacao") or "(s/ prog)"
        return (
            f"#{a['id']} | {a.get('nome_paciente','(s/ nome)')} | "
            f"{a['data_visita']} {hc} | Estudo: {est_txt} | Prog: {prog} | Tipo: {tipo_txt} | Visita: {visita}"
        )

    options = {_fmt_opt(a): a for a in agends}
    key = st.selectbox("Selecione um agendamento", list(options.keys()))
    sel = options[key]

    st.write("\n")
    st.subheader("Detalhes do agendamento")
    colA, colB, colC = st.columns(3)
    with colA:
        st.write(f"**ID:** {sel['id']}")
        st.write(f"**Paciente:** {sel.get('nome_paciente')}")
        st.write(f"**ID Paciente:** {sel.get('id_paciente')}")
    with colB:
        st.write(f"**Data visita:** {sel['data_visita']}")
        st.write(f"**Hora consulta:** {sel.get('hora_consulta')}")
        st.write(f"**Responsável (agenda):** {sel.get('responsavel_agendamento_nome')}")
    with colC:
        est_nome = map_estudo.get(sel.get("estudo_id"), "(sem estudo)")
        st.write(f"**Estudo:** {est_nome}")
        st.write(f"**Programação:** {sel.get('programacao')}")
        st.write(f"**Hora chegada:** {_fmt_time_hhmmss(sel.get('hora_chegada'))}")
        st.write(f"**Hora saída:** {_fmt_time_hhmmss(sel.get('hora_saida'))}")

    st.divider()

    # Chegada
    st.subheader("Chegada")
    hora_chegada_new = st.time_input("Atualizar hora de chegada", value=None, key="hora_chegada_input")
    if st.button("Salvar hora de chegada", use_container_width=True):
        if hora_chegada_new is None:
            st.warning("Selecione uma hora.")
        else:
            ts = f"{sel['data_visita']} {str(hora_chegada_new)}"
            client.table("ag_agendamentos").update({"hora_chegada": ts}).eq("id", sel["id"]).execute()
            st.success("Hora de chegada atualizada.")
            st.rerun()

    st.divider()

    # Financeiro
    st.subheader("Financeiro")
    f1, f2 = st.columns(2)
    with f1:
        valor_new = st.number_input(
            "Valor (R$)",
            value=float(sel.get("valor") or 0.0),
            step=0.5,
            format="%.2f",
            key="inp_valor",
        )
    with f2:
        valor_fin_new = st.number_input(
            "Valor financeiro (R$)",
            value=float(sel.get("valor_financeiro") or 0.0),
            step=0.5,
            format="%.2f",
            key="inp_valor_fin",
        )

    if st.button("Salvar valores", use_container_width=True):
        client.table("ag_agendamentos").update({
            "valor": float(valor_new),
            "valor_financeiro": float(valor_fin_new),
        }).eq("id", sel["id"]).execute()
        st.success("Valores atualizados.")
        st.rerun()

    st.divider()

    # Status por etapa
    st.subheader("Status por etapa")
    atuais = status_atual_por_etapa(sel["id"])
    novos = {}
    for etapa in ETAPAS:
        tipos = listar_status_da_etapa(etapa)
        labels = [t["nome_status"] for t in tipos]
        cur = atuais.get(etapa)
        novos[etapa] = st.selectbox(
            etapa.replace("_", " ").title(),
            options=["(sem alteração)"] + labels,
            index=(labels.index(cur) + 1) if cur in labels else 0,
            key=f"sel_{etapa}",
        )

    if st.button("Registrar alterações de status", use_container_width=True, type="primary"):
        algo_mudou = False
        for etapa, novo in novos.items():
            if novo == "(sem alteração)":
                continue
            if atuais.get(etapa) == novo:
                continue
            payload = {
                "agendamento_id": sel["id"],
                "nome_etapa": etapa,
                "status_etapa": novo,
                "usuario_alteracao_id": user["id"],
                "usuario_alteracao_nome": user["username"],
            }
            client.table("ag_log_agendamentos").insert(payload).execute()
            algo_mudou = True
        if algo_mudou:
            atualizar_hora_saida(sel["id"])
            st.success("Status atualizados e log registrado.")
            st.rerun()

    st.divider()

    # Desfecho
    st.subheader("Desfecho do atendimento")
    desfechos = listar_variaveis_por_grupo("Desfecho_atendimento") or []
    atual_id = sel.get("desfecho_atendimento_id")
    opts = [{"id": None, "nome_variavel": "(selecione)"}] + desfechos
    idx = 0
    if atual_id:
        for i, d in enumerate(opts):
            if d["id"] == atual_id:
                idx = i
                break

    desfecho_sel = st.selectbox(
        "Definir/alterar desfecho",
        options=opts,
        index=idx,
        format_func=lambda x: x["nome_variavel"],
        key="desfecho_sel",
    )

    if st.button("Salvar desfecho", use_container_width=True):
        if desfecho_sel["id"] is None:
            st.warning("Selecione um desfecho válido.")
        else:
            client.table("ag_agendamentos").update({
                "desfecho_atendimento_id": desfecho_sel["id"]
            }).eq("id", sel["id"]).execute()
            st.success("Desfecho atualizado.")
            st.rerun()

    st.divider()

    # Histórico
    st.subheader("Histórico (log)")
    logs = (
        client.table("ag_log_agendamentos")
        .select("nome_etapa, status_etapa, data_hora_etapa, usuario_alteracao_nome")
        .eq("agendamento_id", sel["id"])
        .order("data_hora_etapa", desc=True)
        .limit(1000)
        .execute()
        .data
        or []
    )
    if logs:
        df = pd.DataFrame(logs)
        df["data_hora_etapa"] = (
            pd.to_datetime(df["data_hora_etapa"], errors="coerce", utc=True)
              .dt.tz_convert("America/Sao_Paulo")
              .dt.strftime("%d/%m/%Y %H:%M:%S")
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Sem histórico para este agendamento.")

    st.divider()

    # Excluir (gerência)
    if user["role"] == "gerencia":
        st.error("⚠️ Ação perigosa: Excluir agendamento")
        if st.button("Excluir este agendamento", type="secondary"):
            client.table("ag_log_agendamentos").delete().eq("agendamento_id", sel["id"]).execute()
            client.table("ag_agendamentos").delete().eq("id", sel["id"]).execute()
            st.success("Agendamento excluído.")
            st.rerun()

# =======================================================================================
# ABA 2 — RELATÓRIO (todos os campos + tempos por etapa) — corrigido TZ e colunas padronizadas
# =======================================================================================
with aba_rel:
    st.subheader("Relatório (padronizado) + tempos por etapa")

    ETAPAS_TEMPO = [
        "status_enfermagem",
        "status_coordenacao",
        "status_espirometria",
        "status_farmacia",
        "status_medico",
        "status_nutricionista",
    ]
    STATUS_INICIO = {"Atendendo", "Em atendimento"}

    # ---------- Helpers de TZ ----------
    def parse_ts_utc(val):
        """Converte qualquer string para Timestamp com tz=UTC ou None."""
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        ts = pd.to_datetime(val, errors="coerce", utc=True)
        if pd.isna(ts):
            return None
        return ts

    def ensure_utc(ts):
        """Garante tz=UTC (tz-aware)."""
        if ts is None:
            return None
        if not isinstance(ts, pd.Timestamp):
            ts = pd.to_datetime(ts, errors="coerce")
        if ts is None or pd.isna(ts):
            return None
        if ts.tzinfo is None:
            return ts.tz_localize("UTC")
        return ts.tz_convert("UTC")

    def hhmm_from_seconds(total_seconds: float) -> str:
        if pd.isna(total_seconds) or total_seconds is None:
            return "00:00"
        total_seconds = int(total_seconds)
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        return f"{h:02d}:{m:02d}"

    # ---------- Dados ----------
    ag_ids = [a["id"] for a in agends]
    logs_all = (
        client.table("ag_log_agendamentos")
        .select("agendamento_id, nome_etapa, status_etapa, data_hora_etapa")
        .in_("agendamento_id", ag_ids)
        .in_("nome_etapa", ETAPAS_TEMPO)
        .order("agendamento_id")
        .order("nome_etapa")
        .order("data_hora_etapa")
        .limit(100000)
        .execute()
        .data
        or []
    )

    df_ag = pd.DataFrame(agends)

    # Mapas de texto
    def _map_dict(grupo):
        lst = listar_variaveis_por_grupo(grupo) or []
        return {x["id"]: x["nome_variavel"] for x in lst}

    map_reembolso   = _map_dict("Reembolso")
    map_medico      = _map_dict("Medico_responsavel")
    map_jejum       = _map_dict("Jejum")
    map_desfecho    = _map_dict("Desfecho_atendimento")
    map_consultorio = _map_dict("Consultorio")

    # Colunas texto correspondentes
    df_ag["Estudo"]              = df_ag["estudo_id"].map(map_estudo).fillna("(sem estudo)")
    df_ag["Reembolso"]           = df_ag["reembolso_id"].map(map_reembolso).fillna("(não informado)")
    df_ag["Tipo de visita"]      = df_ag["tipo_visita_id"].map(map_tipo_visita).fillna("(não informado)")
    df_ag["Médico responsável"]  = df_ag["medico_responsavel_id"].map(map_medico).fillna("(não informado)")
    df_ag["Consultório"]         = df_ag["consultorio_id"].map(map_consultorio).fillna("(não informado)")
    df_ag["Jejum"]               = df_ag["jejum_id"].map(map_jejum).fillna("(não informado)")
    df_ag["Desfecho atendimento"]= df_ag["desfecho_atendimento_id"].map(map_desfecho).fillna("(não definido)")

    # Remove IDs brutos que já têm texto
    for col in ["estudo_id","reembolso_id","tipo_visita_id","medico_responsavel_id","consultorio_id","jejum_id","desfecho_atendimento_id"]:
        if col in df_ag.columns:
            del df_ag[col]

    # Campos de participante
    df_ag["ID participante"]   = df_ag["id_paciente"]
    df_ag["Nome participante"] = df_ag["nome_paciente"]

    # Formatação de data/hora pedida
    if "data_cadastro" in df_ag.columns:
        df_ag["Data cadastro"] = pd.to_datetime(df_ag["data_cadastro"], errors="coerce").dt.strftime("%d/%m/%Y %H:%M:%S")
    else:
        df_ag["Data cadastro"] = ""

    df_ag["Hora chegada (local)"] = (
        pd.to_datetime(df_ag["hora_chegada"], errors="coerce", utc=True)
        .dt.tz_convert("America/Sao_Paulo")
        .dt.strftime("%d/%m/%Y %H:%M:%S")
    )
    df_ag["Hora saída (local)"] = (
        pd.to_datetime(df_ag["hora_saida"], errors="coerce", utc=True)
        .dt.tz_convert("America/Sao_Paulo")
        .dt.strftime("%d/%m/%Y %H:%M:%S")
    )

    # ---------- Cálculo de tempos/últimos status com TZ robusto ----------
    df_logs = pd.DataFrame(logs_all)
    if not df_logs.empty:
        df_logs["ts"] = df_logs["data_hora_etapa"].apply(parse_ts_utc)
        df_logs = df_logs.dropna(subset=["ts"])

        # hora_saida bruta (UTC) para cálculo
        raw_saida = pd.DataFrame(agends)[["id", "hora_saida"]]
        raw_saida["hora_saida_ts"] = pd.to_datetime(raw_saida["hora_saida"], errors="coerce", utc=True)

        now_utc = pd.Timestamp(datetime.now(timezone.utc))
        df_logs_sorted = df_logs.sort_values(["agendamento_id", "nome_etapa", "ts"])

        last_status = (
            df_logs_sorted.groupby(["agendamento_id", "nome_etapa"])["status_etapa"]
            .last()
            .reset_index()
            .rename(columns={"status_etapa": "ultimo_status"})
        )

        durations = []
        for (ag_id, etapa), grp in df_logs_sorted.groupby(["agendamento_id", "nome_etapa"]):
            grp = grp.reset_index(drop=True)
            total_sec = 0.0
            for i, row in grp.iterrows():
                if row["status_etapa"] not in STATUS_INICIO:
                    continue
                t_ini = ensure_utc(row["ts"])
                if i + 1 < len(grp):
                    t_fim = ensure_utc(grp.loc[i + 1, "ts"])
                else:
                    rs = raw_saida.loc[raw_saida["id"] == ag_id, "hora_saida_ts"]
                    t_fim = ensure_utc(rs.values[0]) if len(rs) and pd.notna(rs.values[0]) else now_utc
                if t_ini is None or t_fim is None:
                    continue
                # >>>> Fix tz: ambos são tz-aware UTC aqui
                delta = (t_fim - t_ini).total_seconds()
                if delta > 0:
                    total_sec += delta
            durations.append({"agendamento_id": ag_id, "nome_etapa": etapa, "tempo_sec": total_sec})

        df_dur = pd.DataFrame(durations)
        df_stage = pd.merge(df_dur, last_status, on=["agendamento_id", "nome_etapa"], how="left")

        # Tabela de tempos (HH:MM)
        pivot_time = (
            df_stage.pivot_table(
                index="agendamento_id",
                columns="nome_etapa",
                values="tempo_sec",
                aggfunc="sum",
                fill_value=0.0,
            )
            .reindex(columns=ETAPAS_TEMPO, fill_value=0.0)
            .reset_index()
        )
        for etapa in ETAPAS_TEMPO:
            pivot_time[f"Tempo {etapa.split('_',1)[1].title()} (HH:MM)"] = pivot_time[etapa].apply(hhmm_from_seconds)
            del pivot_time[etapa]

        # Último status por etapa
        pivot_last = (
            df_stage.pivot_table(
                index="agendamento_id",
                columns="nome_etapa",
                values="ultimo_status",
                aggfunc="last",
            )
            .reindex(columns=ETAPAS_TEMPO)
            .reset_index()
        )
        for etapa in ETAPAS_TEMPO:
            pivot_last.rename(columns={etapa: f"Último {etapa.split('_',1)[1].title()}"}, inplace=True)

        # Total geral HH:MM
        sum_sec = (
            df_stage.pivot_table(
                index="agendamento_id",
                columns="nome_etapa",
                values="tempo_sec",
                aggfunc="sum",
                fill_value=0.0,
            )
            .reindex(columns=ETAPAS_TEMPO, fill_value=0.0)
            .sum(axis=1)
            .reset_index(name="total_sec")
        )
        sum_sec["Total (HH:MM)"] = sum_sec["total_sec"].apply(hhmm_from_seconds)
        sum_sec = sum_sec.drop(columns=["total_sec"])
    else:
        pivot_time = pd.DataFrame({"agendamento_id": [a["id"] for a in agends]})
        pivot_last = pd.DataFrame({"agendamento_id": [a["id"] for a in agends]})
        sum_sec = pd.DataFrame({"agendamento_id": [a["id"] for a in agends], "Total (HH:MM)": "00:00"})

    # ---------- Montagem do relatório com colunas padronizadas ----------
    # Campos clínicos
    clin_cols = ["Estudo", "Tipo de visita", "Visita", "Médico responsável", "Consultório", "Jejum", "Desfecho atendimento"]
    # Participante
    part_cols = ["ID participante", "Nome participante"]
    df_ag["ID participante"] = df_ag["id_paciente"]
    df_ag["Nome participante"] = df_ag["nome_paciente"]
    # Agendamento/operacional
    op_cols = [
        "Data cadastro", "Data visita", "Hora consulta", "Programação", "Horário Uber",
        "Hora chegada (local)", "Hora saída (local)", "Responsável_agendamento_nome"
    ]
    # Financeiro
    fin_cols = ["Valor", "Valor financeiro", "Reembolso"]

    # Renomeia campos brutos para rótulos amigáveis
    rename_base = {
        "data_visita": "Data visita",
        "hora_consulta": "Hora consulta",
        "programacao": "Programação",
        "horario_uber": "Horário Uber",
        "responsavel_agendamento_nome": "Responsável_agendamento_nome",
        "valor": "Valor",
        "valor_financeiro": "Valor financeiro",
        "visita": "Visita",
    }
    df_ag = df_ag.rename(columns=rename_base)

    base_cols = []
    for c in clin_cols + part_cols + op_cols + fin_cols:
        if c in df_ag.columns:
            base_cols.append(c)

    # DataFrame base ordenado
    rel_base = df_ag.copy()
    if "Data visita" in rel_base.columns and "Hora consulta" in rel_base.columns:
        rel_base = rel_base.sort_values(["Data visita", "Hora consulta", "id"])

    # Junta tempos / últimos status / total
    rel = rel_base.rename(columns={"id": "agendamento_id"}) \
        .merge(pivot_time, on="agendamento_id", how="left") \
        .merge(pivot_last, on="agendamento_id", how="left") \
        .merge(sum_sec, on="agendamento_id", how="left")

    # Colunas finais desejadas (em blocos)
    tempo_cols = [c for c in rel.columns if c.startswith("Tempo ")]
    ultimo_cols = [c for c in rel.columns if c.startswith("Último ")]
    ordered_cols = base_cols + tempo_cols + ultimo_cols + ["Total (HH:MM)"]
    # Garante que não perdemos cols extras relevantes
    ordered_cols = [c for c in ordered_cols if c in rel.columns]

    st.dataframe(rel[ordered_cols], use_container_width=True, hide_index=True)

    csv = rel[ordered_cols].to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Baixar CSV do relatório (padronizado)",
        data=csv,
        file_name="relatorio_agendamentos_padronizado.csv",
        mime="text/csv",
        use_container_width=True,
    )

# =======================================================================================
# ABA 3 — EDIÇÃO (GERÊNCIA)
# =======================================================================================
with aba_edit:
    if user["role"] != "gerencia":
        st.info("Apenas o perfil **gerencia** pode editar os campos de lançamento.")
        st.stop()

    st.subheader("Editar campos de lançamento (Gerência)")

    def _fmt_opt2(a):
        hc = a.get("hora_consulta") or "--:--:--"
        est_txt = map_estudo.get(a.get("estudo_id"), "(sem estudo)")
        tipo_txt = map_tipo_visita.get(a.get("tipo_visita_id"), "(s/ tipo)")
        visita = a.get("visita") or "(s/ visita)"
        prog = a.get("programacao") or "(s/ prog)"
        return (
            f"#{a['id']} | {a.get('nome_paciente','(s/ nome)')} | "
            f"{a['data_visita']} {hc} | Estudo: {est_txt} | Prog: {prog} | Tipo: {tipo_txt} | Visita: {visita}"
        )

    options2 = {_fmt_opt2(a): a for a in agends}
    key2 = st.selectbox("Selecione um agendamento para editar", list(options2.keys()), key="edit_sel")
    sel2 = options2[key2]

    op_estudo       = listar_variaveis_por_grupo("Estudo") or []
    op_reembolso    = listar_variaveis_por_grupo("Reembolso") or []
    op_tipo_visita  = listar_variaveis_por_grupo("Tipo_visita") or []
    op_medico       = listar_variaveis_por_grupo("Medico_responsavel") or []
    op_consultorio  = listar_variaveis_por_grupo("Consultorio") or []
    op_jejum        = listar_variaveis_por_grupo("Jejum") or []

    def _idx(lst, idval):
        base = [{"id": None, "nome_variavel": "(selecione)"}] + lst
        for i, it in enumerate(base):
            if it["id"] == idval:
                return i, base
        return 0, base

    i_est, lst_est = _idx(op_estudo,       sel2.get("estudo_id"))
    i_reb, lst_reb = _idx(op_reembolso,    sel2.get("reembolso_id"))
    i_tip, lst_tip = _idx(op_tipo_visita,  sel2.get("tipo_visita_id"))
    i_med, lst_med = _idx(op_medico,       sel2.get("medico_responsavel_id"))
    i_con, lst_con = _idx(op_consultorio,  sel2.get("consultorio_id"))
    i_jej, lst_jej = _idx(op_jejum,        sel2.get("jejum_id"))

    with st.form("frm_edit_gerencia", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            data_visita   = st.date_input("Data da visita", value=pd.to_datetime(sel2.get("data_visita")).date() if sel2.get("data_visita") else None)
            id_paciente   = st.text_input("ID Paciente",   value=sel2.get("id_paciente") or "")
            nome_paciente = st.text_input("Nome do paciente", value=sel2.get("nome_paciente") or "")
        with c2:
            estudo = st.selectbox("Estudo", options=lst_est, index=i_est, format_func=lambda x: x["nome_variavel"])
            tipo_visita = st.selectbox("Tipo de visita", options=lst_tip, index=i_tip, format_func=lambda x: x["nome_variavel"])
            reembolso = st.selectbox("Reembolso", options=lst_reb, index=i_reb, format_func=lambda x: x["nome_variavel"])
        with c3:
            medico_resp = st.selectbox("Médico responsável", options=lst_med, index=i_med, format_func=lambda x: x["nome_variavel"])
            consultorio = st.selectbox("Consultório", options=lst_con, index=i_con, format_func=lambda x: x["nome_variavel"])
            jejum = st.selectbox("Jejum", options=lst_jej, index=i_jej, format_func=lambda x: x["nome_variavel"])

        c4, c5, c6 = st.columns(3)
        with c4:
            hora_consulta = st.time_input("Hora da consulta", value=pd.to_datetime(sel2.get("hora_consulta")).time() if sel2.get("hora_consulta") else None)
            horario_uber  = st.time_input("Horário do Uber", value=pd.to_datetime(sel2.get("horario_uber")).time() if sel2.get("horario_uber") else None)
        with c5:
            visita     = st.text_input("Visita", value=sel2.get("visita") or "")
            obs_visita = st.text_input("Obs. da visita", value=sel2.get("obs_visita") or "")
        with c6:
            obs_coleta = st.text_input("Obs. de coleta", value=sel2.get("obs_coleta") or "")

        submitted = st.form_submit_button("Salvar alterações", type="primary", use_container_width=True)

    if submitted:
        payload = {
            "data_visita": str(data_visita) if data_visita else None,
            "estudo_id": estudo["id"] if estudo and estudo.get("id") else None,
            "id_paciente": id_paciente.strip() if id_paciente else None,
            "nome_paciente": nome_paciente.strip() if nome_paciente else None,
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
        }
        client.table("ag_agendamentos").update(payload).eq("id", sel2["id"]).execute()
        st.success("Agendamento atualizado.")
        st.rerun()
