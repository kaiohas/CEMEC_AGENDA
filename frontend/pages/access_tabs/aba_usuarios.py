# ============================================================
# 🧍 frontend/pages/access_tabs/aba_usuarios.py
# Gestão de Usuários
# ============================================================
import streamlit as st
import pandas as pd
from frontend.supabase_client import get_supabase_client
from frontend.components.feedback import feedback
from frontend.components.login import hash_password_bcrypt as hash_password


def aba_usuarios(usuario_logado: str):
    st.subheader("🧍 Gestão de Usuários")

    try:
        supabase = get_supabase_client()
        
        # Busca todos os usuários
        response = supabase.table("tab_app_usuarios").select("*").execute()
        df_usuarios = pd.DataFrame(response.data) if response.data else pd.DataFrame()
        
    except Exception as e:
        feedback(f"❌ Erro ao carregar usuários: {e}", "error", "⚠️")
        return

    if df_usuarios.empty:
        st.warning("Nenhum usuário cadastrado ainda.")
        return

    # Normaliza colunas
    df_usuarios.columns = [c.upper() for c in df_usuarios.columns]
    df_usuarios = df_usuarios.sort_values("NM_USUARIO")

    # =====================================================
    # 👁️ VISUALIZAÇÃO
    # =====================================================
    st.markdown("### 👁️ Usuários Cadastrados")
    
    # Filtro por status
    filtro_status = st.radio("Filtrar por status:", ["Todos", "Ativos", "Inativos"], horizontal=True)
    
    if filtro_status == "Ativos":
        df_display = df_usuarios[df_usuarios["SN_ATIVO"] == True]
    elif filtro_status == "Inativos":
        df_display = df_usuarios[df_usuarios["SN_ATIVO"] == False]
    else:
        df_display = df_usuarios

    # Adiciona coluna de status com ícone
    df_display = df_display.copy()
    df_display["STATUS"] = df_display["SN_ATIVO"].apply(lambda x: "🟢 Ativo" if x else "🔴 Inativo")
    
    st.dataframe(
        df_display[["NM_USUARIO", "DS_EMAIL", "NM_USUARIO_LABEL", "STATUS"]],
        use_container_width=True,
        hide_index=True
    )

    # =====================================================
    # ➕ CRIAR NOVO USUÁRIO
    # =====================================================
    st.markdown("---")
    st.markdown("### ➕ Criar Novo Usuário")
    
    with st.form("form_novo_usuario"):
        col1, col2 = st.columns(2)
        
        with col1:
            nm_usuario = st.text_input("Nome de usuário (único)", placeholder="joao_silva")
            ds_email = st.text_input("Email", placeholder="joao@empresa.com")
        
        with col2:
            nm_usuario_label = st.text_input("Nome completo", placeholder="João Silva")
            ds_senha = st.text_input("Senha", type="password", placeholder="Mínimo 8 caracteres")
        
        if st.form_submit_button("✅ Criar Usuário", use_container_width=True):
            if not nm_usuario or not ds_email or not ds_senha or not nm_usuario_label:
                st.error("⚠️ Todos os campos são obrigatórios")
            elif len(ds_senha) < 8:
                st.error("⚠️ Senha deve ter no mínimo 8 caracteres")
            else:
                try:
                    supabase = get_supabase_client()
                    
                    # Verifica se usuário já existe
                    existing = supabase.table("tab_app_usuarios").select("id_usuario").eq("nm_usuario", nm_usuario).execute()
                    if existing.data:
                        st.error("❌ Este nome de usuário já existe")
                        return
                    
                    # Cria novo usuário
                    supabase.table("tab_app_usuarios").insert({
                        "nm_usuario": nm_usuario.lower(),
                        "ds_email": ds_email.lower(),
                        "nm_usuario_label": nm_usuario_label,
                        "ds_senha": hash_password(ds_senha),
                        "sn_ativo": True,
                        "tp_tema": "light"
                    }).execute()
                    
                    feedback(f"✅ Usuário '{nm_usuario}' criado com sucesso!", "success", "🎉")
                    st.rerun()
                    
                except Exception as e:
                    feedback(f"❌ Erro ao criar usuário: {e}", "error", "⚠️")

    # =====================================================
    # 🔄 EDITAR USUÁRIO
    # =====================================================
    st.markdown("---")
    st.markdown("### ✏️ Editar Usuário")
    
    usuario_sel = st.selectbox("Selecione o usuário", df_usuarios["NM_USUARIO"].tolist())
    
    if usuario_sel:
        usuario_data = df_usuarios[df_usuarios["NM_USUARIO"] == usuario_sel].iloc[0]
        
        with st.form(f"form_editar_{usuario_sel}"):
            col1, col2 = st.columns(2)
            
            with col1:
                novo_nome_label = st.text_input(
                    "Nome completo",
                    value=usuario_data.get("NM_USUARIO_LABEL", "")
                )
                novo_email = st.text_input(
                    "Email",
                    value=usuario_data.get("DS_EMAIL", "")
                )
                
                # ✅ NOVO: Campo de senha (opcional)
                nova_senha = st.text_input(
                    "Nova Senha (deixe em branco para manter a atual)",
                    type="password",
                    placeholder="Digite aqui apenas se quiser mudar a senha"
                )
            
            with col2:
                novo_tema = st.radio("Tema", ["light", "dark"], 
                    index=0 if usuario_data.get("TP_TEMA") == "light" else 1
                )
                novo_status = st.checkbox(
                    "Ativo",
                    value=bool(usuario_data.get("SN_ATIVO", True))
                )
            
            if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                # ✅ VALIDAÇÃO: Se digitar senha, deve ter no mínimo 8 caracteres
                if nova_senha and len(nova_senha) < 8:
                    st.error("⚠️ A nova senha deve ter no mínimo 8 caracteres")
                else:
                    try:
                        supabase = get_supabase_client()
                        
                        # Prepara payload
                        payload = {
                            "nm_usuario_label": novo_nome_label,
                            "ds_email": novo_email.lower(),
                            "tp_tema": novo_tema,
                            "sn_ativo": novo_status
                        }
                        
                        # ✅ ADICIONA SENHA APENAS SE FOR FORNECIDA
                        if nova_senha:
                            payload["ds_senha"] = hash_password(nova_senha)
                        
                        supabase.table("tab_app_usuarios").update(payload).eq("nm_usuario", usuario_sel).execute()
                        
                        feedback(f"✅ Usuário '{usuario_sel}' atualizado!", "success", "💾")
                        st.rerun()
                        
                    except Exception as e:
                        feedback(f"❌ Erro ao atualizar: {e}", "error", "⚠️")