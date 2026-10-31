"""
app.py - Radar de Obras PÉMSA (Aplicação de Inteligência Comercial e Prospeção)
Interface Interativa em Streamlit com Sincronização Real, Auditoria de Integridade e Gestão de Conflitos
"""

import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import streamlit as st
import pandas as pd
import json
import io
import base64
import urllib.parse
import importlib
from datetime import date, datetime, timedelta
from PIL import Image

import database
import scrapers
import seed_data

importlib.reload(database)
importlib.reload(scrapers)
importlib.reload(seed_data)

from database import (
    init_db,
    listar_obras,
    obter_obra_por_id,
    listar_empresas,
    listar_tarefas,
    listar_alertas,
    obter_estatisticas_kpi,
    inserir_obra,
    atualizar_status_obra,
    atualizar_intervenientes_obra,
    atualizar_score_obra,
    adicionar_tarefa,
    concluir_tarefa,
    marcar_alerta_processado,
    executar_sincronizacao_radar,
    obter_ultimo_relatorio_sincronizacao,
    listar_registos_suspeitos,
    limpar_atribuicoes_nao_verificadas_obra,
    resolver_conflito_obra,
    exportar_backup_json,
    obter_config,
    get_connection,
    ESTADOS_VERIFICACAO_VALIDOS,
)
from pemsa_catalog import CATALOGO_PEMSA
from scrapers import analisar_texto_obra

icon_path = os.path.join(CURRENT_DIR, "pemsa_icon.png")
if os.path.exists(icon_path):
    try:
        icon_arg = Image.open(icon_path)
    except Exception:
        icon_arg = "⚡"
else:
    icon_arg = "⚡"

st.set_page_config(
    page_title="Radar de Obras PÉMSA 🇵🇹",
    page_icon=icon_arg,
    layout="wide",
    initial_sidebar_state="expanded"
)

if os.path.exists(icon_path):
    with open(icon_path, "rb") as _f:
        _b64_icon = base64.b64encode(_f.read()).decode("utf-8")
    st.markdown(f"""
    <link rel="apple-touch-icon" sizes="192x192" href="data:image/png;base64,{_b64_icon}">
    <link rel="apple-touch-icon-precomposed" sizes="192x192" href="data:image/png;base64,{_b64_icon}">
    <link rel="icon" type="image/png" sizes="192x192" href="data:image/png;base64,{_b64_icon}">
    """, unsafe_allow_html=True)

# Inicializar Base de Dados e Auditoria Não-Destrutiva (sem injetar dados de demonstração no arranque)
init_db()

# Estilos CSS personalizados inspirados na App de Gestão CRI (Tailwind / Slate / Plus Jakarta Sans)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    .stApp {
        background-color: #F8FAFC !important;
    }
    
    /* Forçar títulos do corpo a ficarem sempre escuros e nítidos */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        color: #0F172A !important;
        font-weight: 800 !important;
    }
    
    /* Header Principal Executivo (Garante texto branco sobre fundo escuro) */
    .pemsa-header-container {
        background: #0F172A !important;
        border-radius: 18px !important;
        padding: 18px 24px !important;
        margin-bottom: 24px !important;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25) !important;
        border: 1px solid #1E293B !important;
        color: #FFFFFF !important;
    }
    .pemsa-header-container * {
        color: inherit;
    }
    .pemsa-header-title {
        font-size: 1.85rem !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
        letter-spacing: -0.5px !important;
        margin-bottom: 0.1rem !important;
    }
    .pemsa-header-badge {
        background: rgba(220, 38, 38, 0.25) !important;
        color: #F87171 !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        padding: 3px 8px !important;
        border-radius: 9999px !important;
        border: 1px solid rgba(220, 38, 38, 0.4) !important;
    }
    .pemsa-header-sub {
        font-size: 0.95rem !important;
        color: #94A3B8 !important;
        font-weight: 500 !important;
        margin-bottom: 0 !important;
    }
    
    /* Cartões Modernos de Indicadores (KPIs estilo CRI) */
    .kpi-card {
        background: #FFFFFF;
        padding: 1.25rem 1.4rem;
        border-radius: 18px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02), 0 1px 2px rgba(0,0,0,0.03);
        transition: all 0.2s ease-in-out;
        text-align: left;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.06);
        border-color: #CBD5E1;
    }
    .kpi-num {
        font-size: 2.1rem;
        font-weight: 800;
        color: #0F172A;
        line-height: 1.1;
    }
    .kpi-label {
        font-size: 0.82rem;
        text-transform: uppercase;
        font-weight: 700;
        color: #64748B;
        letter-spacing: 0.6px;
        margin-bottom: 4px;
    }
    .kpi-sub {
        font-size: 0.8rem;
        font-weight: 600;
        margin-top: 6px;
    }

    /* Cartões de Obra Modernos */
    .obra-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 18px;
        padding: 22px;
        margin-bottom: 18px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        transition: all 0.2s ease-in-out;
    }
    .obra-card:hover {
        border-color: #CBD5E1;
        box-shadow: 0 12px 20px -5px rgba(0,0,0,0.07);
        transform: translateY(-2px);
    }

    /* ============================================================ */
    /* OTIMIZAÇÕES MOBILE & RESPONSIVIDADE (SMARTPHONES E TABLETS) */
    /* ============================================================ */
    @media (max-width: 768px) {
        /* Espaçamento geral do ecrã móvel */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }

        /* Header Executivo compacto no telemóvel */
        .pemsa-header-container {
            padding: 14px 16px !important;
            border-radius: 14px !important;
            margin-bottom: 16px !important;
        }
        .main-header {
            font-size: 1.35rem !important;
        }
        .sub-header {
            font-size: 0.82rem !important;
        }

        /* Garantir que as colunas de métricas / cartões quebram em 2 por linha no telemóvel */
        [data-testid="column"] {
            min-width: 46% !important;
            margin-bottom: 8px !important;
        }

        /* Cartões de Indicadores mais compactos e legíveis */
        .kpi-card {
            padding: 1rem 0.8rem !important;
            border-radius: 14px !important;
        }
        .kpi-num {
            font-size: 1.65rem !important;
        }
        .kpi-label {
            font-size: 0.72rem !important;
        }
        .kpi-sub {
            font-size: 0.72rem !important;
        }

        /* Botão de menu lateral sempre visível no topo esquerdo do telemóvel */
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"] {
            top: 0.5rem !important;
            left: 0.5rem !important;
            background: #0F172A !important;
            color: #FFFFFF !important;
            border-radius: 10px !important;
            padding: 4px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        }
        [data-testid="collapsedControl"] svg,
        [data-testid="stSidebarCollapsedControl"] svg {
            fill: #FFFFFF !important;
        }
        
        /* Botões do menu lateral mais fáceis de tocar no ecrã tátil */
        [data-testid="stSidebar"] button {
            padding-top: 10px !important;
            padding-bottom: 10px !important;
            font-size: 0.92rem !important;
        }
    }
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    
    /* Moldura elegante para o Logo na Sidebar */
    .sidebar-logo-box {
        background: #FFFFFF;
        border: 1px solid #F1F5F9;
        border-radius: 16px;
        padding: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.04);
        margin-bottom: 14px;
        text-align: center;
    }
    
    /* Menu de Navegação na Barra Lateral estilo App de Futebol */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 8px !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label {
        display: flex !important;
        align-items: center !important;
        background: #F8FAFC !important;
        border: 1.5px solid #E2E8F0 !important;
        border-radius: 14px !important;
        padding: 10px 14px !important;
        margin: 0 !important;
        cursor: pointer !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:hover {
        background: #F1F5F9 !important;
        border-color: #CBD5E1 !important;
        transform: translateX(4px) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.06) !important;
    }
    
    /* Item Selecionado / Ativo */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked),
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label[data-checked="true"] {
        background: #FEF2F2 !important;
        border-color: #EF4444 !important;
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.12) !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) p,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label[data-checked="true"] p {
        color: #DC2626 !important;
        font-weight: 800 !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label p {
        color: #334155 !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        margin: 0 !important;
        letter-spacing: -0.2px !important;
    }
    
    /* Esconder o círculo de rádio padrão em todas as versões do Streamlit */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child:not([data-testid="stMarkdownContainer"]) {
        display: none !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] input[type="radio"] {
        display: none !important;
    }
    
    /* Caixa de Resumo na Sidebar */
    .sidebar-resumo-box {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 10px;
    }
    .sidebar-resumo-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 5px 0;
        border-bottom: 1px dashed #E2E8F0;
        font-size: 0.82rem;
    }
    .sidebar-resumo-item:last-child {
        border-bottom: none;
    }

    .badge-alta {
        background-color: #DCFCE7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.82rem;
        display: inline-block;
    }
    .badge-media {
        background-color: #FEF9C3;
        color: #854D0E;
        padding: 4px 10px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.82rem;
        display: inline-block;
    }
    .badge-baixa {
        background-color: #F1F5F9;
        color: #475569;
        padding: 4px 10px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.82rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)


def renderizar_badges_integridade(obra):
    """Gera HTML de badges para distinguir oportunidades Reais vs DEMO, estado de verificação e conflitos."""
    origem = obra.get("origem_registo") or "REAL"
    verif = obra.get("estado_verificacao") or "Por verificar"
    conflito = bool(obra.get("tem_conflito", 0))

    if origem == "DEMO":
        b_orig = '<span style="background:#FFF7ED; color:#9A3412; border:1px solid #FDBA74; padding:2px 8px; border-radius:6px; font-size:0.76rem; font-weight:700;">🟠 Registo de Demonstração (DEMO)</span>'
    else:
        b_orig = '<span style="background:#ECFDF5; color:#065F46; border:1px solid #6EE7B7; padding:2px 8px; border-radius:6px; font-size:0.76rem; font-weight:700;">🟢 Oportunidade Real</span>'

    if verif == "Confirmado por contacto direto":
        b_ver = '<span style="background:#DBEAFE; color:#1E40AF; padding:2px 8px; border-radius:6px; font-size:0.76rem; font-weight:700; margin-left:5px;">✔️ Confirmado por contacto direto</span>'
    elif verif == "Confirmado por fonte":
        b_ver = '<span style="background:#E0F2FE; color:#0369A1; padding:2px 8px; border-radius:6px; font-size:0.76rem; font-weight:700; margin-left:5px;">📄 Confirmado por fonte</span>'
    else:
        b_ver = '<span style="background:#FEF3C7; color:#92400E; padding:2px 8px; border-radius:6px; font-size:0.76rem; font-weight:700; margin-left:5px;">🔎 Contacto/Dados: Por verificar</span>'

    b_conf = ""
    if conflito:
        b_conf = '<span style="background:#FEE2E2; color:#991B1B; border:1px solid #FCA5A5; padding:2px 8px; border-radius:6px; font-size:0.76rem; font-weight:700; margin-left:5px;">⚠️ Conflito entre Fontes</span>'

    return f"{b_orig}{b_ver}{b_conf}"


def renderizar_relatorio_sincronizacao(rel):
    """
    Apresenta o relatório transparente de sincronização com hora de início/fim,
    fontes consultadas, sucessos, falhas, contagens e mensagens de erro acionáveis.
    Diferencia claramente 'Sucesso', 'Sucesso parcial' e 'Falha'.
    """
    if not rel:
        return

    estado = rel.get("estado_global", "Falha")
    if estado == "Sucesso":
        st.success(
            f"🟢 **Sincronização Real: SUCESSO** — Todas as {rel.get('fontes_consultadas', 0)} fontes públicas responderam corretamente."
        )
    elif estado == "Sucesso parcial":
        st.warning(
            f"🟡 **Sincronização Real: SUCESSO PARCIAL** — {rel.get('fontes_sucesso', 0)} de {rel.get('fontes_consultadas', 0)} fontes responderam com sucesso ({rel.get('fontes_erro', 0)} com erro)."
        )
    else:
        st.error(
            f"🔴 **Sincronização Real: FALHA** — Nenhuma das {rel.get('fontes_consultadas', 0)} fontes pôde ser consultada. Verifique a ligação de rede ou os erros abaixo."
        )

    with st.expander("📊 Ver Detalhes da Sincronização (Fontes, Contagens, Horários e Erros)", expanded=(estado != "Sucesso" or st.session_state.get("acabou_de_sincronizar", False))):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fontes (OK / Total)", f"{rel.get('fontes_sucesso', 0)} / {rel.get('fontes_consultadas', 0)}", f"{rel.get('fontes_erro', 0)} erros")
        c2.metric("Notícias Encontradas", rel.get("noticias_encontradas", 0))
        c3.metric("Obras Criadas / Atualizadas", f"+{rel.get('obras_criadas', 0)} / ↻{rel.get('obras_atualizadas', 0)}")
        c4.metric("Alertas p/ Validação / Duplicados", f"{rel.get('alertas_pendentes', 0)} / {rel.get('duplicados_ignorados', 0)}")

        st.caption(
            f"⏱️ **Hora de Início:** `{rel.get('inicio_ts', 'N/D')}` &nbsp;|&nbsp; "
            f"**Hora de Fim:** `{rel.get('fim_ts', 'N/D')}` &nbsp;|&nbsp; "
            f"**Modo:** `{rel.get('modo', 'MANUAL')}`"
        )

        rel_fontes = rel.get("relatorios_fontes", [])
        if rel_fontes:
            st.markdown("**Estado Detalhado por Fonte Pública:**")
            for rf in rel_fontes:
                if rf.get("sucesso"):
                    st.markdown(
                        f"- ✅ **{rf['fonte_nome']}** (`{rf['fonte_tipo']}`): HTTP `{rf.get('http_status', 200)}` — "
                        f"**{len(rf.get('itens', []))}** itens recolhidos em `{rf.get('tempo_ms', 0)} ms`"
                    )
                else:
                    st.markdown(
                        f"- ❌ **{rf['fonte_nome']}** (`{rf['fonte_tipo']}`): **Erro:** `{rf.get('erro', 'Erro desconhecido')}`"
                    )


# ----------------- CONTROLO DE ACESSO (PIN CONFIGURÁVEL) -----------------
def check_password():
    """Retorna True se o utilizador estiver autenticado, ou exibe o ecrã de login seguro."""
    if st.session_state.get("authenticated", False):
        return True

    st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarNav"] { display: none !important; }
        .stApp { background-color: #F8FAFC !important; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<div style='text-align: center; padding-top: 10px;'>", unsafe_allow_html=True)
            logo_oficial = os.path.join(CURRENT_DIR, "pemsa_logo_full.png")
            if os.path.exists(logo_oficial):
                st.image(logo_oficial, use_container_width=True)
            elif os.path.exists(icon_path):
                st.image(icon_path, width=80)
            
            st.markdown("<h3 style='color: #0F172A; font-weight: 800; margin-top: 15px; margin-bottom: 2px;'>⚡ Radar de Obras</h3>", unsafe_allow_html=True)
            st.markdown("<p style='color: #64748B; font-size: 0.95rem; margin-bottom: 20px;'>Inteligência Comercial & Qualificação Técnica de Obras</p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            with st.form("form_login_radar", clear_on_submit=False):
                pwd_input = st.text_input(
                    "PIN de Acesso:",
                    type="password",
                    placeholder="Introduza o PIN e prima Enter...",
                    help="Prima a tecla Enter ou clique no botão para entrar."
                )
                btn_entrar = st.form_submit_button("🔓 Entrar no Radar", use_container_width=True, type="primary")

                if btn_entrar:
                    senha_correta = os.environ.get("PEMSA_PIN", "2003")
                    try:
                        if hasattr(st, "secrets") and "PASSWORD" in st.secrets:
                            senha_correta = str(st.secrets["PASSWORD"])
                        elif hasattr(st, "secrets") and "PEMSA_PIN" in st.secrets:
                            senha_correta = str(st.secrets["PEMSA_PIN"])
                    except Exception:
                        pass

                    if str(pwd_input).strip() == senha_correta:
                        st.session_state["authenticated"] = True
                        st.rerun()
                    else:
                        st.error("❌ PIN incorreto. Tente novamente.")

            st.markdown("<div style='text-align: center; margin-top: 15px;'>", unsafe_allow_html=True)
            st.caption("🔒 Área reservada e confidencial da equipa comercial PÉMSA.")
            st.markdown("</div>", unsafe_allow_html=True)

    return False


if not check_password():
    st.stop()

st.markdown("""
<style>
    [data-testid="stSidebar"] { display: block !important; }
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        visibility: visible !important;
    }
    
    /* Transformar os rádios da barra lateral em botões de navegação limpos */
    [data-testid="stSidebar"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 8px !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label {
        background-color: #F8FAFC !important;
        border: 1.5px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 10px 14px !important;
        margin: 0 !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        background-color: #F1F5F9 !important;
        border-color: #CBD5E1 !important;
        transform: translateX(3px) !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
        background-color: #FEF2F2 !important;
        border-color: #DC2626 !important;
        box-shadow: 0 2px 6px rgba(220, 38, 38, 0.1) !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {
        color: #DC2626 !important;
        font-weight: 800 !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label p {
        color: #1E293B !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        margin: 0 !important;
    }
    
    /* Esconder o círculo nativo de rádio */
    [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child:not([data-testid="stMarkdownContainer"]) {
        display: none !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label input[type="radio"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- BARRA LATERAL (NAVEGAÇÃO E FILTROS) -----------------
with st.sidebar:
    logo_oficial = os.path.join(CURRENT_DIR, "pemsa_logo_full.png")
    st.markdown('<div class="sidebar-logo-box">', unsafe_allow_html=True)
    if os.path.exists(logo_oficial):
        st.image(logo_oficial, use_container_width=True)
    else:
        st.markdown("## ⚡ **PÉMSA**")
    st.markdown("""
        <div style="margin-top: 4px; display: flex; align-items: center; justify-content: center; gap: 6px;">
            <span style="font-weight: 800; font-size: 0.95rem; color: #0F172A;">RADAR DE OBRAS</span>
            <span style="background: #FEF2F2; color: #DC2626; font-size: 0.65rem; font-weight: 800; padding: 2px 6px; border-radius: 9999px; border: 1px solid #FECACA;">PT</span>
        </div>
        <div style="font-size: 0.72rem; color: #64748B; margin-top: 2px;">Prospeção & Inteligência Comercial</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='font-size:0.75rem; font-weight:800; color:#94A3B8; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:10px;'>Navegação do Sistema</div>", unsafe_allow_html=True)

    if "menu_ativo" not in st.session_state:
        st.session_state["menu_ativo"] = "📊 1. Painel Inicial (Dashboard)"

    paginas_menu = [
        ("📊 1. Painel Inicial", "📊 1. Painel Inicial (Dashboard)"),
        ("🔎 2. Pesquisa de Obras", "🔎 2. Pesquisa de Obras (Radar)"),
        ("🗺️ 3. Mapa de Portugal", "🗺️ 3. Mapa de Portugal"),
        ("📋 4. Ficha da Obra", "📋 4. Ficha da Obra & Dossiê"),
        ("🏢 5. Empresas & Decisores", "🏢 5. Empresas & Decisores"),
        ("📅 6. Plano Comercial", "📅 6. Plano Comercial & Tarefas"),
        ("📡 7. Motor de Recolha", "📡 7. Motor de Recolha & Alertas")
    ]

    for label_curto, valor_completo in paginas_menu:
        ativo = (st.session_state["menu_ativo"] == valor_completo)
        # Se for a página ativa, usa botão Vermelho Primário (como o 'Atualizar Agora'); senão, botão secundário elegante
        tipo_btn = "primary" if ativo else "secondary"
        if st.button(label_curto, key=f"btn_nav_{valor_completo}", use_container_width=True, type=tipo_btn):
            st.session_state["menu_ativo"] = valor_completo
            st.rerun()

    menu_opcao = st.session_state["menu_ativo"]

    st.markdown("<hr style='margin: 16px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.75rem; font-weight:800; color:#94A3B8; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px;'>🎯 Filtros Rápidos</div>", unsafe_allow_html=True)
    filtro_regiao_global = st.selectbox("Região:", ["Todas", "Norte", "Centro", "Sul", "Madeira", "Açores"], index=0)
    incluir_demo_global = st.checkbox(
        "Mostrar registos de demonstração (DEMO)",
        value=True,
        help="Desative para ver apenas as oportunidades reais recolhidas das fontes públicas."
    )

    kpis = obter_estatisticas_kpi(incluir_demo=incluir_demo_global)
    st.markdown(f"""
    <div class="sidebar-resumo-box">
        <div style="font-size: 0.75rem; font-weight: 800; color: #475569; text-transform: uppercase; margin-bottom: 6px;">Resumo em Tempo Real</div>
        <div class="sidebar-resumo-item">
            <span style="color:#64748B;">Obras Visíveis</span>
            <span style="font-weight:700; color:#0F172A;">{kpis['total_obras']} <span style="font-size:0.72rem; color:#059669;">({kpis['obras_reais']} Reais)</span></span>
        </div>
        <div class="sidebar-resumo-item">
            <span style="color:#64748B;">Alta Prioridade</span>
            <span style="font-weight:700; color:#0F172A;">{kpis['prioritarias']}</span>
        </div>
        <div class="sidebar-resumo-item">
            <span style="color:#64748B;">Contactos p/ Verificar</span>
            <span style="font-weight:700; color:#D97706;">{kpis['contactos_por_identificar']}</span>
        </div>
        <div class="sidebar-resumo-item">
            <span style="color:#64748B;">Tarefas em Atraso</span>
            <span style="font-weight:700; color:#DC2626;">{kpis['tarefas_atrasadas']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if kpis.get("obras_com_conflito", 0) > 0:
        st.warning(f"⚠️ Conflitos de Fontes: **{kpis['obras_com_conflito']}**")

    st.markdown("<hr style='margin: 16px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
    if st.button("🚪 Bloquear / Terminar Sessão", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

# =====================================================================
# 1. PAINEL INICIAL (DASHBOARD)
# =====================================================================
if "1. Painel Inicial" in menu_opcao:
    ult_sync_ts = obter_config("ultima_sincronizacao_ts") or obter_config("ultima_sincronizacao") or "Nunca sincronizado"
    ult_estado = obter_config("ultimo_estado_sync") or "Por sincronizar"
    ic_est = "🟢" if ult_estado == "Sucesso" else ("🟡" if ult_estado == "Sucesso parcial" else "🔴")

    # Header Executivo Estilo App de Futebol com estilos inline diretos (indestrutível contra overrides)
    st.markdown(f"""
    <div style="background: #0F172A; border-radius: 18px; padding: 20px 24px; margin-bottom: 24px; box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25); border: 1px solid #1E293B;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.9rem; font-weight: 900; color: #FFFFFF !important; letter-spacing: -0.5px; text-shadow: 0 2px 4px rgba(0,0,0,0.4);">RADAR DE OBRAS</span>
                    <span style="background: rgba(220, 38, 38, 0.35); color: #FFA4A4 !important; font-size: 0.72rem; font-weight: 800; padding: 3px 9px; border-radius: 9999px; border: 1px solid rgba(220, 38, 38, 0.6); letter-spacing: 0.5px;">PORTUGAL</span>
                </div>
                <div style="font-size: 0.95rem; color: #CBD5E1 !important; font-weight: 500; margin-top: 4px;">Inteligência Comercial, Qualificação Técnica e Decisores Verificáveis</div>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="background: rgba(30, 41, 59, 0.85); border: 1px solid #334155; padding: 8px 14px; border-radius: 12px; text-align: right;">
                    <div style="font-size: 0.8rem; font-weight: 800; color: #F8FAFC !important;">{ic_est} Sync: {ult_estado}</div>
                    <div style="font-size: 0.72rem; color: #94A3B8 !important;">Consulta: {ult_sync_ts}</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_btn_sync, col_vazio = st.columns([1.5, 4.5])
    with col_btn_sync:
        if st.button("🔄 Atualizar Agora", use_container_width=True, key="btn_sync_dash", type="primary"):
            with st.spinner("A consultar fontes públicas em tempo real (RSS, Notícias Oficiais, Concursos)..."):
                rel_sync = executar_sincronizacao_radar(forcar=True, modo="MANUAL")
                st.session_state["ultimo_relatorio_ui"] = rel_sync
                st.session_state["acabou_de_sincronizar"] = True
                st.rerun()
                st.session_state["acabou_de_sincronizar"] = True

    rel_exibir = st.session_state.get("ultimo_relatorio_ui") or obter_ultimo_relatorio_sincronizacao()
    if rel_exibir:
        renderizar_relatorio_sincronizacao(rel_exibir)
        st.session_state["acabou_de_sincronizar"] = False

    kpis = obter_estatisticas_kpi(incluir_demo=incluir_demo_global)

    # Métricas em 4 colunas com visual moderno estilo CRI Futebol
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Obras no Radar</div>
            <div class="kpi-num">{kpis['total_obras']}</div>
            <div class="kpi-sub" style="color: #059669;">✔️ {kpis['obras_reais']} Verificadas Reais</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Oportunidades</div>
            <div class="kpi-num">{kpis['prioritarias']}</div>
            <div class="kpi-sub" style="color: #64748B;">Prioritárias (Score ≥ 75)</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Contactos</div>
            <div class="kpi-num">{kpis['contactos_por_identificar']}</div>
            <div class="kpi-sub" style="color: #D97706;">⚠️ Por Verificar na Fonte</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Tarefas CRM</div>
            <div class="kpi-num">{kpis['tarefas_atrasadas']}</div>
            <div class="kpi-sub" style="color: #DC2626;">🚨 Seguimentos em Atraso</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    obras = listar_obras(
        regiao=filtro_regiao_global if filtro_regiao_global != "Todas" else None,
        incluir_demo=incluir_demo_global
    )
    if obras:
        obras_reais_lista = [o for o in obras if o.get("origem_registo") == "REAL"]
        top_obra = obras_reais_lista[0] if obras_reais_lista else obras[0]
        top_detalhes = obter_obra_por_id(top_obra['id'])

        st.subheader("💡 Oportunidade em Destaque no Radar")
        with st.container(border=True):
            col_top_info, col_top_score = st.columns([3, 1])
            with col_top_info:
                st.markdown(f"### 📍 **{top_obra['titulo']}**", unsafe_allow_html=True)
                st.markdown(renderizar_badges_integridade(top_obra), unsafe_allow_html=True)
                st.markdown(
                    f"**Localização:** {top_obra['concelho']}, {top_obra['distrito']} ({top_obra['regiao']}) | "
                    f"**Segmento:** `{top_obra['segmento']}` | **Fase:** `{top_obra['fase']}`"
                )

                resp_nome = top_obra.get('responsavel_nome') or 'Por verificar'
                resp_cargo = top_obra.get('responsavel_cargo') or 'Por verificar'
                resp_emp = top_obra.get('responsavel_empresa') or 'Por verificar'
                resp_ct = top_obra.get('responsavel_contacto') or 'Por verificar'
                verif_st = top_obra.get('estado_verificacao') or 'Por verificar'

                st.markdown(f"""
                <div style="background:#FFF5F5; border-left:4px solid #CC2229; padding:10px 14px; border-radius:6px; margin:10px 0;">
                    <span style="font-weight:700; color:#991B1B;">🎯 Prioridade / Contacto ({verif_st}):</span>
                    <span style="font-weight:700; color:#1E293B;"> {resp_nome}</span>
                    <span style="color:#475569; font-size:0.9rem;"> ({resp_cargo})</span>
                    <br><span style="font-weight:700; color:#1E293B;">🏗️ Intervenientes na Fonte:</span> <span style="color:#0F172A; font-weight:600;">{resp_emp}</span>
                    <br><span style="font-size:0.86rem; color:#475569;">☎️ <b>Contacto:</b> {resp_ct}</span>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"**Resumo:** {top_obra['resumo']}")
                st.caption(
                    f"🔗 **Fonte:** [{top_obra.get('fonte_nome')}]({top_obra.get('fonte_url')}) | "
                    f"**Publicação da Fonte:** `{top_obra.get('data_publicacao_fonte') or top_obra.get('data_detecao') or 'Por verificar'}` | "
                    f"**Consulta:** `{top_obra.get('data_consulta_fonte') or 'N/D'}`"
                )

                if top_detalhes and top_detalhes.get('produtos'):
                    prods_txt = ", ".join([p['familia_produto'].split('(')[0].strip() for p in top_detalhes['produtos'][:3]])
                    st.markdown(f"**Potencial PÉMSA:** `{prods_txt}` e acessórios de fixação.")

                st.info(f"👉 **Próxima Ação Comercial:** {top_obra['proxima_acao']}")

            with col_top_score:
                st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
                st.metric("Pontuação PÉMSA", f"{top_obra['score']}/100", f"Prioridade {top_obra['prioridade']}")
                st.caption(f"Valor Est.: {top_obra['valor_estimado'] or 'Por verificar'}")
                if st.button("Ver Dossiê Completo ➡️", key="btn_top_detalhe"):
                    st.session_state["obra_selecionada_id"] = top_obra['id']
                    st.info("Aceda ao menu '4. Ficha da Obra' para ver o dossiê detalhado.")
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Nenhuma obra encontrada para os filtros selecionados. Clique em '🔄 Atualizar Agora' para sincronizar com as fontes públicas.")

    # Tarefas Urgentes e Distribuição
    st.markdown("---")
    col_tarefas, col_radar = st.columns([2, 1])

    with col_tarefas:
        st.subheader("📌 Minhas Tarefas de Prospeção para Hoje")
        tarefas_pendentes = listar_tarefas(apenas_pendentes=True)
        if tarefas_pendentes:
            for t in tarefas_pendentes[:4]:
                today = date.today().isoformat()
                is_atrasada = t['data_limite'] < today
                cor_icone = "🔴" if is_atrasada else ("🟡" if t['data_limite'] == today else "🔵")

                with st.container(border=True):
                    col_t_check, col_t_txt, col_t_act = st.columns([0.5, 3.5, 1])
                    with col_t_check:
                        st.markdown(f"### {cor_icone}")
                    with col_t_txt:
                        st.markdown(f"**{t['titulo']}**")
                        st.caption(f"📅 Limite: {t['data_limite']} | Tipo: `{t['tipo']}` | Obra: {t.get('obra_titulo', 'Geral')}")
                    with col_t_act:
                        if st.button("Concluir", key=f"btn_conc_{t['id']}"):
                            concluir_tarefa(t['id'], "Concluído via painel rápido.")
                            st.rerun()
        else:
            st.success("Não existem tarefas pendentes. Excelente trabalho!")

    with col_radar:
        st.subheader("🎯 Resumo por Segmento")
        df_obras = pd.DataFrame(obras)
        if not df_obras.empty:
            seg_counts = df_obras['segmento'].value_counts()
            st.bar_chart(seg_counts)
        else:
            st.write("Sem dados.")

# =====================================================================
# 2. PESQUISA DE OBRAS (RADAR & FILTROS)
# =====================================================================
elif "2. Pesquisa de Obras" in menu_opcao:
    st.markdown('<div class="main-header">🔎 Radar de Obras em Portugal</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Pesquisa avançada, separação entre oportunidades reais e demonstração, e estado de verificação</div>', unsafe_allow_html=True)

    with st.expander("🛠️ Filtros de Pesquisa e Segmentação", expanded=True):
        fcol1, fcol2, fcol3, fcol4 = st.columns(4)
        with fcol1:
            filtro_segmento = st.selectbox("Segmento de Obra:", [
                "Todos", "Data Center", "Hospital / Saúde", "Industrial / Fábricas",
                "Logística / Armazéns", "Hotel / Turismo", "Energia / Renováveis", "Edifícios Terciários & Públicos"
            ])
        with fcol2:
            filtro_regiao = st.selectbox("Região:", ["Todas", "Norte", "Centro", "Sul", "Madeira", "Açores", "Por verificar"])
        with fcol3:
            filtro_fase = st.selectbox("Fase da Obra:", [
                "Todas", "Projeto de Execução / MEP", "Concurso de Empreitada",
                "Adjudicação / Pré-Construção", "Início de Construção", "Em Obra (Instalações a decorrer)", "Por verificar"
            ])
        with fcol4:
            filtro_prioridade = st.selectbox("Prioridade Comercial:", ["Todas", "Alta", "Média", "Baixa"])

        busca_texto = st.text_input("🔍 Pesquisar por palavra-chave, nome da obra, concelho ou empresa:", "")

    obras_filtradas = listar_obras(
        segmento=filtro_segmento,
        regiao=filtro_regiao,
        fase=filtro_fase,
        prioridade=filtro_prioridade,
        busca=busca_texto if busca_texto else None,
        incluir_demo=incluir_demo_global
    )

    st.write(f"Encontradas **{len(obras_filtradas)}** obras correspondentes aos critérios.")

    tab_cards, tab_tabela = st.tabs(["🗂️ Vista de Cartões Comerciais", "📊 Vista de Tabela Estruturada"])

    with tab_cards:
        if not obras_filtradas:
            st.info("Nenhuma obra encontrada para estes filtros.")
        for obra in obras_filtradas:
            with st.container(border=True):
                c_info, c_score, c_btn = st.columns([3.5, 1.2, 1])

                with c_info:
                    badge_class = "badge-alta" if obra['score'] >= 75 else ("badge-media" if obra['score'] >= 50 else "badge-baixa")
                    st.markdown(f"#### {obra['titulo']}")
                    st.markdown(renderizar_badges_integridade(obra), unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="margin-top:5px;">
                    <span class="{badge_class}">Prioridade {obra['prioridade']} ({obra['score']}/100)</span>
                    <span style="background:#EEF2F6; color:#1E293B; padding:3px 8px; border-radius:5px; font-size:0.8rem; margin-left:6px;">📍 {obra['concelho']}, {obra['distrito']}</span>
                    <span style="background:#EEF2F6; color:#1E293B; padding:3px 8px; border-radius:5px; font-size:0.8rem; margin-left:6px;">🏗️ {obra['segmento']}</span>
                    <span style="background:#F0FDF4; color:#15803D; padding:3px 8px; border-radius:5px; font-size:0.8rem; margin-left:6px;">⏱️ {obra['fase']}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown(f"<p style='color:#475569; margin-top:8px;'>{obra['resumo']}</p>", unsafe_allow_html=True)

                    r_nome = obra.get('responsavel_nome') or 'Por verificar'
                    r_cargo = obra.get('responsavel_cargo') or 'Por verificar'
                    r_emp = obra.get('responsavel_empresa') or 'Por verificar'
                    r_ct = obra.get('responsavel_contacto') or 'Por verificar'
                    st.markdown(f"""
                    <div style="background:#F8FAFC; border-left:3px solid #CC2229; padding:8px 12px; margin:8px 0; border-radius:4px;">
                        <span style="font-weight:700; color:#991B1B;">🎯 Contacto / Prioridade ({obra.get('estado_verificacao') or 'Por verificar'}):</span>
                        <span> <b>{r_nome}</b> <span style="color:#475569; font-size:0.88rem;">({r_cargo})</span></span>
                        <br><span style="font-weight:700; color:#1E293B;">🏗️ Intervenientes:</span> <b>{r_emp}</b>
                        <br><span style="font-size:0.85rem; color:#64748B;">☎️ Contacto: <b>{r_ct}</b></span>
                    </div>
                    """, unsafe_allow_html=True)

                    st.caption(
                        f"🔗 **Fonte:** [{obra['fonte_nome']}]({obra['fonte_url']}) | "
                        f"Pub. Fonte: `{obra.get('data_publicacao_fonte') or obra['data_detecao']}` | "
                        f"Consulta: `{obra.get('data_consulta_fonte') or 'N/D'}` | Ref: `{obra['codigo_ref']}`"
                    )

                with c_score:
                    st.markdown("**Timing Fornecimento:**")
                    st.caption(f"{obra['timing_fornecimento']}")
                    st.markdown("**Próxima Ação:**")
                    st.caption(f"{obra['proxima_acao']}")

                with c_btn:
                    st.markdown(f"**Estado:** `{obra['status_comercial']}`")
                    if st.button("Abrir Ficha 📄", key=f"btn_ver_{obra['id']}", use_container_width=True):
                        st.session_state["obra_selecionada_id"] = obra['id']
                        st.session_state["navegar_para_ficha"] = True
                        st.info("Obra selecionada! Vá a '4. Ficha da Obra' para gerir.")

    with tab_tabela:
        if obras_filtradas:
            df = pd.DataFrame(obras_filtradas)
            colunas_exibir = [
                'id', 'origem_registo', 'estado_verificacao', 'tem_conflito',
                'titulo', 'score', 'prioridade',
                'responsavel_nome', 'responsavel_empresa', 'responsavel_contacto',
                'segmento', 'distrito', 'concelho', 'regiao', 'fase',
                'status_comercial', 'valor_estimado', 'data_publicacao_fonte', 'fonte_url'
            ]
            colunas_presentes = [c for c in colunas_exibir if c in df.columns]
            st.dataframe(df[colunas_presentes], use_container_width=True)

            csv = df[colunas_presentes].to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descarregar Tabela em CSV", csv, "radar_pemsa_obras.csv", "text/csv")
        else:
            st.info("Sem dados para apresentar na tabela.")

# =====================================================================
# 3. MAPA DE PORTUGAL
# =====================================================================
elif "3. Mapa de Portugal" in menu_opcao:
    st.markdown('<div class="main-header">🗺️ Mapa de Obras em Portugal</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Geolocalização e densidade de oportunidades (Norte, Centro, Sul e Ilhas)</div>', unsafe_allow_html=True)

    obras_mapa = listar_obras(
        regiao=filtro_regiao_global if filtro_regiao_global != "Todas" else None,
        incluir_demo=incluir_demo_global
    )
    df_mapa = pd.DataFrame(obras_mapa)

    if not df_mapa.empty and 'lat' in df_mapa.columns and 'lon' in df_mapa.columns:
        df_geo = df_mapa.dropna(subset=['lat', 'lon']).copy()

        col_leg1, col_leg2, col_leg3 = st.columns(3)
        col_leg1.markdown("🟢 **Alta Prioridade (Score >= 75):** Agir Imediatamente")
        col_leg2.markdown("🟡 **Média Prioridade (50 - 74):** Acompanhar Concurso")
        col_leg3.markdown("⚪ **Baixa Prioridade (< 50):** Investigação Passiva")

        if not df_geo.empty:
            st.map(df_geo, latitude='lat', longitude='lon', size=25, zoom=6)

        st.markdown("#### Lista de Obras Geolocalizadas:")
        for _, row in df_geo.iterrows():
            with st.expander(f"📍 {row['titulo']} — {row['distrito']} (Score: {row['score']}/100)"):
                st.write(f"**Origem:** `{row.get('origem_registo', 'REAL')}` | **Segmento:** {row['segmento']} | **Fase:** {row['fase']}")
                st.write(f"**Resumo:** {row['resumo']}")
                st.write(f"**Próxima Ação:** {row['proxima_acao']}")
                if st.button("Ver Dossiê", key=f"map_btn_{row['id']}"):
                    st.session_state["obra_selecionada_id"] = row['id']
                    st.info("Obra selecionada! Vá ao menu '4. Ficha da Obra'.")
    else:
        st.warning("Não há coordenadas disponíveis para exibir no mapa.")

# =====================================================================
# 4. FICHA DA OBRA & DOSSIÊ
# =====================================================================
elif "4. Ficha da Obra" in menu_opcao:
    st.markdown('<div class="main-header">📋 Ficha da Obra & Dossiê Comercial</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Qualificação 360°, verificação de contactos, resolução de conflitos e histórico de fontes</div>', unsafe_allow_html=True)

    todas_obras = listar_obras(incluir_demo=True)
    if not todas_obras:
        st.warning("Nenhuma obra registada na base de dados.")
        st.stop()

    opcoes_obras = {
        o['id']: f"[{'DEMO' if o.get('origem_registo')=='DEMO' else 'REAL'} | {o['score']} pts] {o['titulo']} ({o['distrito']})"
        for o in todas_obras
    }
    obra_id_default = st.session_state.get("obra_selecionada_id", todas_obras[0]['id'])
    if obra_id_default not in opcoes_obras:
        obra_id_default = todas_obras[0]['id']

    obra_id_selecionada = st.selectbox(
        "Selecione a Obra para consultar o Dossiê:",
        options=list(opcoes_obras.keys()),
        format_func=lambda x: opcoes_obras[x],
        index=list(opcoes_obras.keys()).index(obra_id_default)
    )

    obra = obter_obra_por_id(obra_id_selecionada)

    if obra:
        st.markdown("---")

        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown(f"## 🏗️ {obra['titulo']}")
            st.markdown(renderizar_badges_integridade(obra), unsafe_allow_html=True)
            st.markdown(
                f"**Referência:** `{obra['codigo_ref']}` | **Chave Estável:** `{obra.get('chave_estavel') or 'N/D'}` | "
                f"**Segmento:** `{obra['segmento']}` | **Localização:** {obra['morada_localizacao'] or obra['concelho']}, {obra['distrito']} ({obra['regiao']})"
            )
            st.markdown(
                f"**Fonte:** [{obra['fonte_nome']}]({obra['fonte_url']}) | "
                f"**Data Publicação Fonte:** `{obra.get('data_publicacao_fonte') or obra['data_detecao']}` | "
                f"**Data/Hora Consulta:** `{obra.get('data_consulta_fonte') or 'N/D'}`"
            )
        with col_h2:
            st.metric("Pontuação PÉMSA", f"{obra['score']}/100", f"Prioridade {obra['prioridade']}")
            st.progress(obra['score'] / 100)

        if obra.get("origem_registo") == "DEMO":
            col_warn_d1, col_warn_d2 = st.columns([3, 1])
            with col_warn_d1:
                st.warning(
                    "⚠️ **Aviso de Integridade:** Este registo provém da base inicial de demonstração (`DEMO`). "
                    "As empresas ou contactos atribuídos não devem ser assumidos como adjudicados sem verificação documental."
                )
            with col_warn_d2:
                if st.button("🧹 Limpar dados não verificados", key=f"btn_clean_demo_{obra['id']}", use_container_width=True):
                    limpar_atribuicoes_nao_verificadas_obra(obra['id'])
                    st.success("Atribuições não verificadas colocadas como 'Por verificar'. Tarefas e notas foram preservadas!")
                    st.rerun()

        r_nome = obra.get('responsavel_nome') or 'Por verificar'
        r_cargo = obra.get('responsavel_cargo') or 'Por verificar'
        r_emp = obra.get('responsavel_empresa') or 'Por verificar'
        r_ct = obra.get('responsavel_contacto') or 'Por verificar'
        r_verif = obra.get('estado_verificacao') or 'Por verificar'
        lnk_q_ficha = urllib.parse.quote(f"{r_emp.split('|')[0].replace('Projetista:', '').replace('Projetista MEP:', '').replace('Construtor:', '').strip()} Engenharia Eletrotecnica")

        st.markdown(f"""
        <div style="background:#FFF5F5; border:1px solid #FECACA; border-left:5px solid #CC2229; padding:12px 16px; border-radius:8px; margin: 12px 0;">
            <div style="font-size:0.8rem; font-weight:700; color:#991B1B; text-transform:uppercase; letter-spacing:0.5px;">
                🎯 Prioridade de Abordagem & Estado de Verificação: [{r_verif}]
            </div>
            <div style="font-size:1.15rem; font-weight:700; color:#1E293B; margin-top:2px;">{r_nome}</div>
            <div style="color:#475569; font-size:0.95rem; margin-top:4px;">
                <b>2.ª Linha / Cargo:</b> {r_cargo}
            </div>
            <div style="color:#0F172A; font-size:0.98rem; margin-top:6px; background:#FFFFFF; padding:6px 10px; border-radius:5px; border:1px solid #F1F5F9;">
                🏗️ <b>Projetista / Construtor / Instalador:</b> {r_emp}
            </div>
            <div style="color:#475569; font-size:0.9rem; margin-top:6px;">
                ☎️ <b>Contacto:</b> {r_ct} &nbsp;|&nbsp;
                <a href="https://www.linkedin.com/search/results/people/?keywords={lnk_q_ficha}" target="_blank" style="color:#CC2229; font-weight:700; text-decoration:none;">🔗 Pesquisar no LinkedIn ↗</a>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("✏️ Atualizar Projetista, Construtor, Contacto e Estado de Verificação"):
            with st.form(f"form_edit_interv_{obra['id']}"):
                ei_col1, ei_col2 = st.columns(2)
                with ei_col1:
                    novo_resp_nome = st.text_input("Prioridade / Nome Real do Engenheiro ou Comprador:", value=r_nome)
                    novo_resp_emp = st.text_input("Projetista MEP / Construtor / Instalador:", value=r_emp)
                with ei_col2:
                    novo_resp_cargo = st.text_input("2.ª Prioridade / Cargo / Departamento:", value=r_cargo)
                    novo_resp_ct = st.text_input("Telefone / Email Verificado:", value=r_ct)

                idx_ver = list(ESTADOS_VERIFICACAO_VALIDOS).index(r_verif) if r_verif in ESTADOS_VERIFICACAO_VALIDOS else 0
                novo_est_verif = st.selectbox(
                    "Estado de Verificação do Contacto:",
                    options=list(ESTADOS_VERIFICACAO_VALIDOS),
                    index=idx_ver,
                    help="Contactos confirmados manualmente nunca são substituídos pelas atualizações automáticas."
                )
                if st.form_submit_button("💾 Guardar Dados de Contacto e Marcar como Protegido"):
                    atualizar_intervenientes_obra(
                        obra['id'], novo_resp_nome, novo_resp_cargo, novo_resp_emp, novo_resp_ct, estado_verificacao=novo_est_verif
                    )
                    st.success("Dados de contacto e estado de verificação guardados! Protegidos contra substituição automática.")
                    st.rerun()

        with st.container(border=True):
            col_est1, col_est2 = st.columns([2, 3])
            with col_est1:
                estados_lista = [
                    "Nova Oportunidade", "Em Qualificação", "Contacto Feito",
                    "Apresentação Técnica Realizada", "Proposta Enviada", "Ganha (Fornecimento Fechado)", "Perdida", "Arquivada"
                ]
                novo_estado = st.selectbox(
                    "Estado no Pipeline Comercial:",
                    estados_lista,
                    index=estados_lista.index(obra['status_comercial']) if obra['status_comercial'] in estados_lista else 0
                )
            with col_est2:
                novas_notas = st.text_input("Notas Comerciais (Preservadas nas sincronizações):", value=obra.get('notas_comerciais') or "")
            if st.button("💾 Gravar Atualização Comercial"):
                atualizar_status_obra(obra['id'], novo_estado, novas_notas)
                st.success("Estado e notas comerciais atualizados!")
                st.rerun()

        t_scoring, t_empresas, t_produtos, t_tarefas = st.tabs([
            "📊 Pontuação & Justificação Comercial",
            "👥 Cadeia de Decisão & Contactos",
            "⚡ Produtos PÉMSA Recomendados",
            "📅 Tarefas, Conflitos & Histórico de Fontes"
        ])

        with t_scoring:
            st.subheader("Critérios de Avaliação PÉMSA (0 a 100)")
            breakdown_data = json.loads(obra['score_breakdown']) if obra.get('score_breakdown') else None

            if breakdown_data and 'detalhes' in breakdown_data:
                st.markdown(f"**Orientação Estratégica:** {breakdown_data.get('orientacao', '')}")
                for item in breakdown_data['detalhes']:
                    col_cr1, col_cr2, col_cr3 = st.columns([2, 1, 3])
                    col_cr1.markdown(f"**{item['criterio']}**")
                    col_cr2.markdown(f"**{item['pontos']}** / {item['max']} pts")
                    col_cr3.caption(f"{item['justificacao']}")
                    st.divider()
            else:
                st.info("Pontuação calculada pela matriz técnica PÉMSA.")

            st.markdown(f"**Timing de Fornecimento:** {obra['timing_fornecimento']}")
            st.markdown(f"👉 **Ação Prioritária Sugerida:** {obra['proxima_acao']}")

        with t_empresas:
            st.subheader("Cadeia de Decisão e Empresas Envolvidas")
            st.caption("Cada relação indica se foi 'Confirmado por fonte', 'Confirmado por contacto direto' ou se está 'Por verificar'.")

            papeis_ordem = ["Promotor/Dono", "Projetista MEP", "Empreiteiro Geral", "Instalador Elétrico", "Comprador/Distribuidor"]
            empresas_da_obra = obra.get('empresas', [])

            for papel in papeis_ordem:
                emp_papel = [e for e in empresas_da_obra if papel.lower() in e['papel'].lower()]
                with st.container(border=True):
                    st.markdown(f"##### 🏢 {papel}")
                    if emp_papel:
                        for emp in emp_papel:
                            col_e_nome, col_e_contact = st.columns([2, 2])
                            with col_e_nome:
                                ver_rel = emp.get('rel_verificacao') or 'Por verificar'
                                st.markdown(f"**{emp['nome']}** (`{emp['tipo']}`) — *{ver_rel}*")
                                st.write(f"📍 {emp['cidade']}, {emp['distrito']} | Tel Sede: {emp['telefone']}")
                                st.caption(f"Evidência/Notas: {emp.get('rel_notas') or emp.get('notas') or 'Por verificar'}")
                            with col_e_contact:
                                conn = get_connection()
                                cur = conn.cursor()
                                cur.execute("SELECT * FROM contactos WHERE empresa_id = ?", (emp['id'],))
                                cts = cur.fetchall()
                                conn.close()
                                if cts:
                                    st.markdown("**Contactos Associados:**")
                                    for c in cts:
                                        c_dict = dict(c)
                                        st.write(f"👤 **{c_dict['nome']}** — *{c_dict.get('estado_verificacao', 'Por verificar')}*")
                                        st.write(f"📞 {c_dict['telefone']} | ✉️ {c_dict['email']}")
                                else:
                                    st.warning("⚠️ Contactos diretos por verificar.")
                    else:
                        st.info(f"Nenhuma empresa confirmada como '{papel}' (Por verificar).")

        with t_produtos:
            st.subheader("Compatibilidade Técnica com a Gama PÉMSA")
            produtos_obra = obra.get('produtos', [])

            if produtos_obra:
                for p in produtos_obra:
                    with st.container(border=True):
                        col_p1, col_p2 = st.columns([3, 1])
                        with col_p1:
                            st.markdown(f"#### ⚡ {p['familia_produto']}")
                            st.markdown(f"**Detalhe Técnico / Especificação:** {p.get('especificacao_detalhe') or 'Conforme caderno de encargos.'}")
                            cat_info = CATALOGO_PEMSA.get(p['familia_produto'])
                            if cat_info:
                                st.caption(f"💡 **Vantagem Comercial:** {cat_info['vantagem_competitiva']}")
                        with col_p2:
                            st.markdown("**Classificação:**")
                            st.info(f"{p['nivel_potencial']}")
            else:
                st.info("Ainda não foram adicionados produtos específicos a esta obra.")

        with t_tarefas:
            # 1. Conflitos de fontes pendentes de resolução
            historico_obra = obra.get("historico", [])
            conflitos_abertos = [h for h in historico_obra if h.get("acao") == "CONFLITO" and h.get("resolvido", 0) == 0]
            if conflitos_abertos:
                st.error(f"⚠️ Existem **{len(conflitos_abertos)} conflito(s) de informação** detetados entre fontes diferentes para esta obra:")
                for conf in conflitos_abertos:
                    with st.container(border=True):
                        st.markdown(
                            f"**Campo em Divergência:** `{conf['campo']}`  \n"
                            f"- **Valor Atual na Obra:** `{conf['valor_anterior']}`  \n"
                            f"- **Novo Valor Encontrado na Fonte ({conf['fonte_nome']}):** `{conf['valor_novo']}`"
                        )
                        c_cf1, c_cf2 = st.columns(2)
                        with c_cf1:
                            if st.button("✅ Aceitar Novo Valor da Fonte", key=f"btn_acc_conf_{conf['id']}", use_container_width=True):
                                resolver_conflito_obra(obra['id'], conf['id'], aceitar_novo_valor=True)
                                st.success("Novo valor aplicado e conflito resolvido!")
                                st.rerun()
                        with c_cf2:
                            if st.button("🛡️ Manter Valor Atual", key=f"btn_ign_conf_{conf['id']}", use_container_width=True):
                                resolver_conflito_obra(obra['id'], conf['id'], aceitar_novo_valor=False)
                                st.info("Valor atual mantido e conflito encerrado.")
                                st.rerun()

            st.subheader("Tarefas Comerciais para esta Obra")
            tarefas_obra = obra.get('tarefas', [])

            if tarefas_obra:
                for t in tarefas_obra:
                    with st.container(border=True):
                        st.markdown(f"**{t['titulo']}**")
                        st.write(f"📅 Data Limite: `{t['data_limite']}` | Tipo: `{t['tipo']}` | Estado: `{t['estado']}`")
                        if t.get('resultado_interacao'):
                            st.success(f"Resultado: {t['resultado_interacao']}")
                        if t['estado'] == 'Pendente':
                            res_in = st.text_input("Registar Resultado da Ação Comercial:", key=f"res_{t['id']}")
                            if st.button("Marcar Concluída", key=f"btn_conc_obra_{t['id']}"):
                                concluir_tarefa(t['id'], res_in or "Concluída com sucesso.")
                                st.rerun()
            else:
                st.write("Nenhuma tarefa registada.")

            st.markdown("---")
            st.markdown("##### ➕ Nova Tarefa para esta Obra")
            with st.form("form_nova_tarefa_obra"):
                t_tit = st.text_input("Título da Tarefa:", "Contactar para apresentar soluções PÉMSA")
                t_tipo = st.selectbox("Tipo de Ação:", ["Chamada", "Email", "Visita/Reunião", "Apresentação Técnica", "Envio de Amostras", "Envio de Proposta"])
                t_data = st.date_input("Data Limite:", date.today() + timedelta(days=2))
                t_prio = st.selectbox("Prioridade:", ["Normal", "Alta", "Urgente"])
                btn_salvar_t = st.form_submit_button("Agendar Tarefa")
                if btn_salvar_t:
                    adicionar_tarefa(obra['id'], t_tit, t_tipo, t_data.isoformat(), t_prio)
                    st.success("Tarefa agendada!")
                    st.rerun()

            st.markdown("---")
            st.subheader("📜 Histórico de Alterações, Fontes e Auditoria")
            if historico_obra:
                for h in historico_obra:
                    st.markdown(
                        f"- **`[{h['created_at']}]` `{h['acao']}`** no campo **`{h['campo']}`**: "
                        f"de `{h.get('valor_anterior') or 'vazio'}` ➡️ para **`{h.get('valor_novo')}`** "
                        f"*(Fonte: {h.get('fonte_nome') or 'Sistema'})*"
                    )
            else:
                st.caption("Sem alterações de histórico registadas.")

# =====================================================================
# 5. EMPRESAS & DECISORES
# =====================================================================
elif "5. Empresas & Decisores" in menu_opcao:
    st.markdown('<div class="main-header">🏢 Empresas & Decisores Chave</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Mapeamento de Promotores, Projetistas MEP, Empreiteiros e Instaladores em Portugal</div>', unsafe_allow_html=True)

    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        f_tipo_emp = st.selectbox("Filtrar por Papel:", ["Todos", "Promotor", "Projetista MEP", "Empreiteiro Geral", "Instalador Elétrico"])
    with col_f2:
        f_busca_emp = st.text_input("Pesquisar empresa por nome ou localidade:", "")

    empresas = listar_empresas(tipo=f_tipo_emp, busca=f_busca_emp if f_busca_emp else None)

    st.write(f"Total de empresas encontradas: **{len(empresas)}**")

    for emp in empresas:
        with st.expander(f"🏢 {emp['nome']} — {emp['tipo']} ({emp['cidade']}, {emp['distrito']}) [{emp.get('estado_verificacao', 'Por verificar')}]"):
            c_e1, c_e2 = st.columns(2)
            with c_e1:
                st.markdown(f"**NIF:** {emp['nif'] or 'Por verificar'} | **Relação Comercial:** `{emp['nivel_relacionamento']}`")
                st.markdown(f"📞 {emp['telefone']} | ✉️ {emp['email']}")
                st.markdown(f"🌐 [{emp['website']}]({emp['website']})" if emp['website'] else "")
                st.caption(f"Notas: {emp['notas']}")

                if emp.get('obras_participa'):
                    st.markdown("**Obras Associadas:**")
                    for ob in emp['obras_participa']:
                        st.write(f"• [{ob['papel']} — *{ob.get('estado_verificacao', 'Por verificar')}*] {ob['titulo']}")

            with c_e2:
                st.markdown("##### 👤 Departamentos / Contactos Registados")
                if emp.get('contactos'):
                    for ct in emp['contactos']:
                        with st.container(border=True):
                            st.markdown(f"**{ct['nome']}** — *{ct['cargo']}* (`{ct.get('estado_verificacao', 'Por verificar')}`)")
                            st.caption(f"Departamento: {ct['departamento'] or 'Geral'}")
                            st.write(f"📞 {ct['telefone']} | ✉️ {ct['email']}")
                            if ct['linkedin']:
                                st.markdown(f"[Pesquisa / Perfil LinkedIn]({ct['linkedin']})")
                else:
                    st.info("Ainda sem contactos registados para esta empresa (Por verificar).")

# =====================================================================
# 6. PLANO COMERCIAL & TAREFAS
# =====================================================================
elif "6. Plano Comercial" in menu_opcao:
    st.markdown('<div class="main-header">📅 Plano Comercial & Ações de Seguimento</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Gestão de contactos, prazos e histórico de prospeção pessoal (100% preservado nas sincronizações)</div>', unsafe_allow_html=True)

    tarefas = listar_tarefas(apenas_pendentes=False)
    today = date.today().isoformat()

    atrasadas = [t for t in tarefas if t['estado'] == 'Pendente' and t['data_limite'] < today]
    hoje = [t for t in tarefas if t['estado'] == 'Pendente' and t['data_limite'] == today]
    futuras = [t for t in tarefas if t['estado'] == 'Pendente' and t['data_limite'] > today]
    concluidas = [t for t in tarefas if t['estado'] == 'Concluída']

    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    col_k1.metric("⚠️ Em Atraso", len(atrasadas))
    col_k2.metric("📅 Para Hoje", len(hoje))
    col_k3.metric("🔜 Próximos Dias", len(futuras))
    col_k4.metric("✅ Concluídas", len(concluidas))

    tab_pend, tab_concl = st.tabs(["⏳ Tarefas Pendentes", "✅ Histórico de Interações Concluídas"])

    with tab_pend:
        lista_pend = atrasadas + hoje + futuras
        if lista_pend:
            for t in lista_pend:
                is_atr = t['data_limite'] < today
                is_hj = t['data_limite'] == today

                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"#### {'🔴 [EM ATRASO] ' if is_atr else ('🟡 [HOJE] ' if is_hj else '🔵 ')}{t['titulo']}")
                        st.write(f"🏗️ **Obra:** {t.get('obra_titulo', 'Geral')} (Score {t.get('obra_score')})")
                        st.write(f"🏢 **Empresa:** {t.get('empresa_nome', 'Por verificar')} | 👤 **Contacto:** {t.get('contacto_nome', 'Por verificar')} ({t.get('contacto_telefone', '')})")
                        st.caption(f"Data Limite: **{t['data_limite']}** | Ação: `{t['tipo']}` | Prioridade: `{t['prioridade']}`")
                    with c2:
                        res = st.text_input("Resultado:", key=f"res_plan_{t['id']}")
                        if st.button("Marcar Feito ✅", key=f"btn_done_{t['id']}", use_container_width=True):
                            concluir_tarefa(t['id'], res or "Concluído com sucesso.")
                            st.rerun()
        else:
            st.success("Tudo em dia! Nenhuma tarefa pendente.")

    with tab_concl:
        if concluidas:
            for t in concluidas:
                with st.container(border=True):
                    st.markdown(f"**{t['titulo']}**")
                    st.write(f"🏗️ Obra: {t.get('obra_titulo', 'Geral')} | Concluída em: {t['data_conclusao']}")
                    st.success(f"Resultado registado: {t['resultado_interacao']}")
        else:
            st.info("Ainda não há tarefas marcadas como concluídas.")

# =====================================================================
# 7. MOTOR DE RECOLHA & ALERTAS
# =====================================================================
elif "7. Motor de Recolha" in menu_opcao:
    st.markdown('<div class="main-header">📡 Motor de Recolha, Alertas & Auditoria</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Sincronização Real com Fontes Públicas, Validação de Evidência e Relatório de Integridade</div>', unsafe_allow_html=True)

    tab_alertas, tab_auditoria, tab_estrategia, tab_ia, tab_freq, tab_excel = st.tabs([
        "🔔 Alertas Pendentes de Validação",
        "🛡️ Auditoria de Registos Suspeitos (DEMO)",
        "🎯 Matriz Estratégica das Fontes",
        "🤖 Inserir / Analisar Texto de Obra",
        "⏰ Atualização Automática (GitHub Actions / Windows)",
        "📑 Exportar Excel & Backup JSON"
    ])

    # SUBTAB 1: ALERTAS DE RECOLHA REAL
    with tab_alertas:
        col_al_top1, col_al_top2 = st.columns([3, 1.2])
        with col_al_top1:
            st.markdown("##### Notícias Recolhidas que Aguardam Validação Humana (Evidência Parcial)")
            st.caption("Notícias sem localização ou fase explícita ficam aqui retidas para revisão em vez de criarem obras falsas automaticamente.")
        with col_al_top2:
            if st.button("🔄 Atualizar Agora (Sincronização Real)", use_container_width=True, key="btn_sync_motor"):
                with st.spinner("A consultar conectores públicos em tempo real..."):
                    rel_sync = executar_sincronizacao_radar(forcar=True, modo="MANUAL")
                    st.session_state["ultimo_relatorio_ui"] = rel_sync
                    st.session_state["acabou_de_sincronizar"] = True

        rel_motor = st.session_state.get("ultimo_relatorio_ui") or obter_ultimo_relatorio_sincronizacao()
        if rel_motor:
            renderizar_relatorio_sincronizacao(rel_motor)

        mostrar_alertas_demo = st.checkbox("Incluir alertas iniciais de demonstração", value=False)
        alertas = listar_alertas(apenas_nao_processados=True, incluir_demo=mostrar_alertas_demo)
        st.write(f"Alertas pendentes de validação comercial: **{len(alertas)}**")

        for al in alertas:
            with st.container(border=True):
                c_a1, c_a2 = st.columns([3.5, 1])
                with c_a1:
                    badge_al = "🟠 `[DEMO]` " if al.get("origem_registo") == "DEMO" else "🟢 `[FONTE REAL]` "
                    st.markdown(f"#### {badge_al}📢 {al['titulo']}")
                    st.caption(
                        f"Fonte: **{al['fonte_nome']}** ({al['fonte_tipo']}) | "
                        f"Publicado em: `{al.get('data_publicacao') or 'Sem data na fonte'}` | "
                        f"Consultado em: `{al.get('data_consulta') or al.get('created_at')}`"
                    )
                    st.markdown(
                        f"**Promotor Detetado:** `{al.get('entidade_promotora') or 'Por verificar'}` | "
                        f"**Segmento Estimado:** `{al['segmento_estimado']}` | **Região:** `{al['regiao_estimada']}`"
                    )
                    if al.get("motivo_validacao"):
                        st.warning(f"🔎 **Motivo de retenção para validação:** {al['motivo_validacao']}")
                    st.write(al['resumo_bruto'])
                    if al['link']:
                        st.markdown(f"[🔗 Abrir Notícia / Anúncio Original na Fonte]({al['link']})")
                with c_a2:
                    if st.button("Validar e Criar Obra ➕", key=f"btn_aprov_{al['id']}", use_container_width=True):
                        dados_extraidos = analisar_texto_obra(
                            al['titulo'] + ". " + (al['resumo_bruto'] or ""),
                            fonte_nome=al['fonte_nome'],
                            fonte_url=al['link'],
                            data_publicacao=al.get('data_publicacao')
                        )

                        nova_obra_dict = {
                            "titulo": dados_extraidos["titulo"],
                            "codigo_ref": f"PEMSA-VAL-{al['id']}-{int(datetime.now().timestamp())%10000}",
                            "segmento": dados_extraidos["segmento"],
                            "regiao": dados_extraidos["regiao"],
                            "distrito": dados_extraidos["distrito"],
                            "concelho": dados_extraidos["concelho"],
                            "morada_localizacao": f"{dados_extraidos['concelho']}, {dados_extraidos['distrito']}",
                            "lat": None,
                            "lon": None,
                            "fase": dados_extraidos["fase"],
                            "status_comercial": "Em Qualificação",
                            "score": dados_extraidos["score"],
                            "score_breakdown": json.dumps(dados_extraidos["score_breakdown"], ensure_ascii=False),
                            "prioridade": dados_extraidos["prioridade"],
                            "valor_estimado": dados_extraidos.get("valor_estimado") or "Por verificar",
                            "prazo_previsto": "Por verificar",
                            "data_detecao": date.today().isoformat(),
                            "data_publicacao_fonte": al.get("data_publicacao"),
                            "data_consulta_fonte": al.get("data_consulta") or datetime.now().isoformat(timespec="seconds"),
                            "fonte_tipo": al["fonte_tipo"],
                            "fonte_nome": al["fonte_nome"],
                            "fonte_url": al["link"],
                            "resumo": dados_extraidos["resumo"],
                            "timing_fornecimento": dados_extraidos["timing_fornecimento"],
                            "proxima_acao": dados_extraidos["proxima_acao"],
                            "notas_comerciais": "Promovido manualmente a partir dos Alertas de Recolha após validação.",
                            "responsavel_nome": dados_extraidos.get("responsavel_nome") or "Por verificar",
                            "responsavel_cargo": dados_extraidos.get("responsavel_cargo") or "Por verificar",
                            "responsavel_empresa": dados_extraidos.get("responsavel_empresa") or "Por verificar",
                            "responsavel_contacto": dados_extraidos.get("responsavel_contacto") or "Por verificar",
                            "estado_verificacao": dados_extraidos.get("estado_verificacao") or "Por verificar",
                            "origem_registo": "REAL"
                        }

                        nova_id = inserir_obra(nova_obra_dict, produtos_pemsa=dados_extraidos["produtos_sugeridos"])
                        marcar_alerta_processado(al['id'], obra_id=nova_id)
                        st.success(f"Obra validada e adicionada ao Radar! (ID: {nova_id})")
                        st.rerun()

                    if st.button("Descartar ❌", key=f"btn_desc_{al['id']}", use_container_width=True):
                        marcar_alerta_processado(al['id'], obra_id=None)
                        st.rerun()

    # SUBTAB 2: AUDITORIA DE REGISTOS SUSPEITOS / DEMONSTRAÇÃO
    with tab_auditoria:
        st.markdown("##### 🛡️ Relatório de Registos de Demonstração (`DEMO`) e Dados por Verificar")
        st.caption(
            "Nenhum registo existente foi apagado automaticamente para preservar as suas tarefas e notas comerciais. "
            "Aqui pode rever todos os registos pré-populados de demonstração e limpar atribuições não verificadas."
        )
        registos_susp = listar_registos_suspeitos()
        st.write(f"Total de registos sinalizados para revisão: **{len(registos_susp)}**")

        for rs in registos_susp:
            with st.container(border=True):
                c_rs1, c_rs2 = st.columns([3.5, 1.2])
                with c_rs1:
                    st.markdown(f"#### [{rs['codigo_ref']}] {rs['titulo']}")
                    st.markdown(renderizar_badges_integridade(rs), unsafe_allow_html=True)
                    st.write(
                        f"**Intervenientes atuais:** `{rs.get('responsavel_empresa')}`  \n"
                        f"**Contacto atual:** `{rs.get('responsavel_contacto')}`  \n"
                        f"**URL Fonte atual:** `{rs.get('fonte_url')}`"
                    )
                    if rs.get("notas_comerciais"):
                        st.caption(f"📝 Notas comerciais preservadas: {rs['notas_comerciais']}")
                with c_rs2:
                    if st.button("🧹 Limpar atribuições não verificadas", key=f"aud_clean_{rs['id']}", use_container_width=True):
                        limpar_atribuicoes_nao_verificadas_obra(rs['id'])
                        st.success(f"Registo {rs['codigo_ref']} limpo para 'Por verificar'!")
                        st.rerun()
                    if st.button("Abrir na Ficha 📄", key=f"aud_open_{rs['id']}", use_container_width=True):
                        st.session_state["obra_selecionada_id"] = rs['id']
                        st.info("Selecione o menu '4. Ficha da Obra' na barra lateral.")

    # SUBTAB 3: MATRIZ ESTRATÉGICA DAS FONTES
    with tab_estrategia:
        st.markdown("##### 🎯 Matriz Estratégica das Fontes de Informação PÉMSA")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            with st.container(border=True):
                st.markdown("#### 1. 🌿 SIAIA (APA) & PARTICIPA")
                st.markdown("- **Momento:** 6 a 18 meses antes da obra física.\n- **Objetivo:** Prescrição técnica junto do projetista MEP.")
            with st.container(border=True):
                st.markdown("#### 2. 🇪🇺 TED — Tenders Electronic Daily")
                st.markdown("- **Momento:** Fase de Concurso Público internacional.\n- **Objetivo:** Orçamentação com empreiteiros e instaladores.")
        with col_f2:
            with st.container(border=True):
                st.markdown("#### 3. 🏛️ Portal BASE & Diário da República")
                st.markdown("- **Momento:** Anúncio de procedimento e adjudicação.\n- **Objetivo:** Abordagem direta ao adjudicatário confirmado.")
            with st.container(border=True):
                st.markdown("#### 4. 📰 Imprensa Económica (RSS Verificado)")
                st.markdown("- **Momento:** Anúncio de investimento privado (fábricas, logística, data centers).\n- **Objetivo:** Qualificação inicial e validação de promotores.")

    # SUBTAB 4: ANALISAR COM IA / REGRAS BASEADAS EM EVIDÊNCIA
    with tab_ia:
        st.markdown("##### 🤖 Extração Baseada em Evidência (Sem Invenção de Contactos)")
        st.caption("Cole o texto de um anúncio oficial ou notícia. Campos não comprovados pelo texto serão marcados como 'Por verificar'.")

        texto_input = st.text_area(
            "Cole o texto da notícia ou anúncio de concurso:",
            height=150,
            value="Município de Vila Nova de Gaia lança concurso público para a empreitada de construção do novo Centro de Saúde no valor de 2,4 milhões de euros."
        )
        url_input = st.text_input("URL específico da fonte (opcional):", "")

        if st.button("🔍 Analisar Evidência do Texto", use_container_width=True):
            analise = analisar_texto_obra(texto_input, fonte_nome="Análise Manual de Fonte", fonte_url=url_input)
            st.session_state["ultima_analise_ia"] = analise

        if "ultima_analise_ia" in st.session_state:
            res_ia = st.session_state["ultima_analise_ia"]
            if res_ia.get("evidencia_suficiente_obra"):
                st.success(f"✅ Evidência suficiente para Obra: {res_ia.get('motivo_evidencia')}")
            else:
                st.warning(f"⚠️ Evidência parcial ({res_ia.get('motivo_evidencia')}) — Recomenda-se guardar como Alerta ou completar os campos 'Por verificar'.")

            with st.container(border=True):
                col_r1, col_r2 = st.columns([3, 1])
                with col_r1:
                    st.markdown(f"### 📍 {res_ia['titulo']}")
                    st.write(
                        f"**Segmento:** `{res_ia['segmento']}` | **Localização:** `{res_ia['concelho']}, {res_ia['distrito']} ({res_ia['regiao']})` | "
                        f"**Fase:** `{res_ia['fase']}` | **Valor:** `{res_ia['valor_estimado']}`"
                    )
                    st.markdown(f"""
                    <div style="background:#F8FAFC; border-left:3px solid #CC2229; padding:8px 12px; margin:6px 0; border-radius:4px;">
                        <b>🎯 Estado de Verificação:</b> {res_ia.get('estado_verificacao')}<br>
                        <b>👤 Contacto Citado:</b> {res_ia.get('responsavel_nome')}<br>
                        <b>🏗️ Entidades Citadas na Fonte:</b> {res_ia.get('responsavel_empresa')}
                    </div>
                    """, unsafe_allow_html=True)
                    st.info(f"👉 **Próxima Ação Sugerida:** {res_ia['proxima_acao']}")

                with col_r2:
                    st.metric("Pontuação Estimada", f"{res_ia['score']}/100", f"Prioridade {res_ia['prioridade']}")
                    if st.button("💾 Gravar no Radar de Obras", key="btn_save_ia_obra", use_container_width=True):
                        nova_obra_dict = {
                            "titulo": res_ia["titulo"],
                            "codigo_ref": f"PEMSA-MAN-{datetime.now().strftime('%m%d%H%M%S')}",
                            "segmento": res_ia["segmento"],
                            "regiao": res_ia["regiao"],
                            "distrito": res_ia["distrito"],
                            "concelho": res_ia["concelho"],
                            "morada_localizacao": f"{res_ia['concelho']}, {res_ia['distrito']}",
                            "lat": None,
                            "lon": None,
                            "fase": res_ia["fase"],
                            "status_comercial": "Nova Oportunidade",
                            "score": res_ia["score"],
                            "score_breakdown": json.dumps(res_ia["score_breakdown"], ensure_ascii=False),
                            "prioridade": res_ia["prioridade"],
                            "valor_estimado": res_ia["valor_estimado"],
                            "prazo_previsto": "Por verificar",
                            "data_detecao": date.today().isoformat(),
                            "data_publicacao_fonte": res_ia.get("data_publicacao"),
                            "data_consulta_fonte": res_ia.get("data_consulta"),
                            "fonte_tipo": "Inserção Verificada",
                            "fonte_nome": res_ia["fonte_nome"],
                            "fonte_url": res_ia["fonte_url"],
                            "resumo": res_ia["resumo"],
                            "timing_fornecimento": res_ia["timing_fornecimento"],
                            "proxima_acao": res_ia["proxima_acao"],
                            "notas_comerciais": None,
                            "responsavel_nome": res_ia.get("responsavel_nome"),
                            "responsavel_cargo": res_ia.get("responsavel_cargo"),
                            "responsavel_empresa": res_ia.get("responsavel_empresa"),
                            "responsavel_contacto": res_ia.get("responsavel_contacto"),
                            "estado_verificacao": res_ia.get("estado_verificacao"),
                            "origem_registo": "REAL"
                        }
                        nova_id = inserir_obra(nova_obra_dict, produtos_pemsa=res_ia["produtos_sugeridos"])
                        st.success(f"Obra gravada no Radar com ID {nova_id}!")
                        st.rerun()

    # SUBTAB 5: ATUALIZAÇÃO AUTOMÁTICA INDEPENDENTE DO BROWSER
    with tab_freq:
        st.markdown("##### ⏰ Sincronização Automática Independente do Browser")
        st.markdown("""
        O Radar PÉMSA possui um motor autónomo (`atualizar_radar.py`) que executa sem depender de ninguém ter o browser aberto:
        1. **GitHub Actions (Nuvem — Diário às 07:00 UTC):** Ficheiro `.github/workflows/sync_radar.yml` configurado para correr automaticamente todos os dias, consultar as fontes públicas e atualizar a base de dados do repositório.
        2. **Agendador de Tarefas do Windows (PC Local):**
           ```powershell
           schtasks /Create /SC DAILY /TN "RadarPEMSA_Sync" /TR "python C:\\Users\\PauloAlmeida\\.gemini\\antigravity\\scratch\\radar_pemsa\\atualizar_radar.py" /ST 08:00 /F
           ```
        3. **Execução Manual em Linha de Comandos:**
           ```powershell
           python atualizar_radar.py
           ```
        """)

    # SUBTAB 6: EXPORTAÇÃO EXCEL & BACKUP JSON
    with tab_excel:
        st.markdown("##### 📑 Exportação de Relatório Excel (.xlsx) e Backup de Persistência (.json)")
        obras_exp = listar_obras(incluir_demo=incluir_demo_global)
        if obras_exp:
            df_exp = pd.DataFrame(obras_exp)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_exp.to_excel(writer, sheet_name='Radar Obras PEMSA', index=False)
            output.seek(0)

            st.download_button(
                label="📥 Descarregar Folha de Cálculo Excel (.xlsx)",
                data=output,
                file_name=f"Radar_Obras_PEMSA_{date.today().isoformat()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        st.markdown("---")
        st.markdown("##### 💾 Backup Completo da Base de Dados (Proteção para Ambientes Cloud Efémeros)")
        backup_str = exportar_backup_json()
        st.download_button(
            label="📦 Descarregar Backup Integral (JSON — Obras, Tarefas, Notas e Histórico)",
            data=backup_str.encode("utf-8"),
            file_name=f"backup_radar_pemsa_{date.today().isoformat()}.json",
            mime="application/json",
            use_container_width=True
        )
