"""
app.py - Radar de Obras PÉMSA (Aplicação de Inteligência Comercial e Prospeção)
Interface Interativa em Streamlit
"""

import sys
import os

# Garantir que o diretório atual do projeto está no sys.path (essencial para o Linux / Streamlit Cloud)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import streamlit as st
import pandas as pd
import json
import io
import base64
from datetime import date, datetime, timedelta
from PIL import Image

from database import (
    init_db, listar_obras, obter_obra_por_id, listar_empresas,
    listar_tarefas, listar_alertas, obter_estatisticas_kpi,
    inserir_obra, atualizar_status_obra, atualizar_score_obra,
    adicionar_tarefa, concluir_tarefa, marcar_alerta_processado,
    verificar_e_executar_sincronizacao_automatica,
    get_connection
)
from pemsa_catalog import CATALOGO_PEMSA, avaliar_compatibilidade_pemsa
from scoring import calcular_score_obra
from scrapers import analisar_texto_obra, simular_rastreio_alertas
import seed_data

icon_path = os.path.join(CURRENT_DIR, "pemsa_icon.png")
if os.path.exists(icon_path):
    try:
        icon_arg = Image.open(icon_path)
    except Exception:
        icon_arg = "⚡"
else:
    icon_arg = "⚡"

# Configuração da página Streamlit com ícone oficial da PÉMSA
st.set_page_config(
    page_title="Radar de Obras PÉMSA 🇵🇹",
    page_icon=icon_arg,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injeção de meta tags para Apple iOS / iPhone (apple-touch-icon)
if os.path.exists(icon_path):
    with open(icon_path, "rb") as _f:
        _b64_icon = base64.b64encode(_f.read()).decode("utf-8")
    st.markdown(f"""
    <link rel="apple-touch-icon" sizes="192x192" href="data:image/png;base64,{_b64_icon}">
    <link rel="apple-touch-icon-precomposed" sizes="192x192" href="data:image/png;base64,{_b64_icon}">
    <link rel="icon" type="image/png" sizes="192x192" href="data:image/png;base64,{_b64_icon}">
    """, unsafe_allow_html=True)

# Inicializar Base de Dados e dados iniciais se necessário
init_db()
seed_data.popular_dados_iniciais()

# Verificação e Atualização Automática Periódica (Segunda-feira ou nova semana)
atualizou_auto, qtd_novos = verificar_e_executar_sincronizacao_automatica()
if atualizou_auto and qtd_novos > 0:
    st.toast(f"⚡ Radar PÉMSA: {qtd_novos} novos alertas de obras adicionados automaticamente esta semana!", icon="📡")

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    .kpi-card {
        background: #FFFFFF;
        padding: 1.2rem;
        border-radius: 10px;
        border-left: 5px solid #2563EB;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        text-align: center;
    }
    .kpi-num {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E293B;
    }
    .kpi-label {
        font-size: 0.85rem;
        text-transform: uppercase;
        font-weight: 600;
        color: #64748B;
        letter-spacing: 0.5px;
    }
    .badge-alta {
        background-color: #DCFCE7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
    }
    .badge-media {
        background-color: #FEF9C3;
        color: #854D0E;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
    }
    .badge-baixa {
        background-color: #F1F5F9;
        color: #475569;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
    }
    .obra-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        transition: transform 0.15s ease-in-out;
    }
    .obra-card:hover {
        border-color: #CBD5E1;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.08);
    }
</style>
""", unsafe_allow_html=True)

# ----------------- CONTROLO DE ACESSO (PALAVRA-PASSE) -----------------
def check_password():
    """Retorna True se o utilizador estiver autenticado, ou exibe o ecrã de login seguro."""
    if st.session_state.get("authenticated", False):
        return True

    # Ocultar sidebar e comandos durante o ecrã de login
    st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none; }
        [data-testid="stSidebarNav"] { display: none; }
        [data-testid="collapsedControl"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
            if os.path.exists(icon_path):
                st.image(icon_path, width=80)
            st.markdown("<h2 style='color: #CC2229; margin-bottom: 2px;'>⚡ Radar PÉMSA</h2>", unsafe_allow_html=True)
            st.markdown("<p style='color: #64748B; font-size: 0.95rem; margin-bottom: 15px;'>Acesso Restrito — Prospeção Comercial</p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            pwd_input = st.text_input("PIN de Acesso:", type="password", placeholder="Introduza o PIN de 4 dígitos...")
            
            senha_correta = "2003"
            try:
                if hasattr(st, "secrets") and "PASSWORD" in st.secrets:
                    senha_correta = str(st.secrets["PASSWORD"])
            except Exception:
                pass

            if st.button("🔓 Entrar no Radar", use_container_width=True, type="primary"):
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

# ----------------- BARRA LATERAL (NAVEGAÇÃO E FILTROS) -----------------
with st.sidebar:
    logo_path = os.path.join(os.path.dirname(__file__), "pemsa_logo.svg")
    if os.path.exists(logo_path):
        st.image(logo_path, width=170)
    else:
        st.markdown("## ⚡ **PÉMSA**")
    st.markdown("<h3 style='margin-top: -10px; color: #CC2229;'>Radar de Obras</h3>", unsafe_allow_html=True)
    st.caption("Inteligência Comercial de Obras — Portugal")

    menu_opcao = st.radio(
        "Navegação do Sistema:",
        [
            "📊 1. Painel Inicial (Dashboard)",
            "🔎 2. Pesquisa de Obras (Radar)",
            "🗺️ 3. Mapa de Portugal",
            "📋 4. Ficha da Obra & Dossiê",
            "🏢 5. Empresas & Decisores",
            "📅 6. Plano Comercial & Tarefas",
            "📡 7. Motor de Recolha & Alertas"
        ],
        index=0
    )

    st.markdown("---")
    st.markdown("##### 🎯 **Filtro Global Rápido**")
    filtro_regiao_global = st.selectbox("Região:", ["Todas", "Norte", "Centro", "Sul", "Madeira", "Açores"], index=0)

    st.markdown("---")
    kpis = obter_estatisticas_kpi()
    st.markdown(f"**Resumo em Tempo Real:**")
    st.write(f"• Obras no Radar: **{kpis['total_obras']}**")
    st.write(f"• Alta Prioridade: **{kpis['prioritarias']}**")
    st.write(f"• Tarefas em Atraso: **{kpis['tarefas_atrasadas']}**")
    st.caption("Versão 1.0 MVP — Prospeção Pessoal PÉMSA")

    st.markdown("---")
    if st.button("🚪 Bloquear / Terminar Sessão", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

# =====================================================================
# 1. PAINEL INICIAL (DASHBOARD)
# =====================================================================
if "1. Painel Inicial" in menu_opcao:
    col_tit1, col_tit2 = st.columns([4, 1])
    with col_tit1:
        st.markdown('<div class="main-header"><span style="color:#CC2229;">⚡ RADAR PÉMSA</span> — Obras em Portugal</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">Inteligência Comercial, Qualificação Técnica e Decisores Chave</div>', unsafe_allow_html=True)

    kpis = obter_estatisticas_kpi()

    # Métricas em 4 colunas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #2563EB;">
            <div class="kpi-num" style="color: #2563EB;">{kpis['total_obras']}</div>
            <div class="kpi-label">Novas Obras no Radar</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #16A34A;">
            <div class="kpi-num" style="color: #16A34A;">{kpis['prioritarias']}</div>
            <div class="kpi-label">Oportunidades Prioritárias</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #EAB308;">
            <div class="kpi-num" style="color: #CA8A04;">{kpis['contactos_por_identificar']}</div>
            <div class="kpi-label">Decisores por Mapear</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #DC2626;">
            <div class="kpi-num" style="color: #DC2626;">{kpis['tarefas_atrasadas']}</div>
            <div class="kpi-label">Seguimentos em Atraso</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Oportunidade Sugerida (Destaque do Dia)
    obras = listar_obras(regiao=filtro_regiao_global if filtro_regiao_global != "Todas" else None)
    if obras:
        top_obra = obras[0] # Maior score
        top_detalhes = obter_obra_por_id(top_obra['id'])

        st.subheader("💡 Oportunidade Sugerida para Esta Semana")
        with st.container(border=True):
            col_top_info, col_top_score = st.columns([3, 1])
            with col_top_info:
                st.markdown(f"### 📍 **{top_obra['titulo']}**")
                st.markdown(f"**Localização:** {top_obra['concelho']}, {top_obra['distrito']} ({top_obra['regiao']}) | **Segmento:** `{top_obra['segmento']}` | **Fase:** `{top_obra['fase']}`")
                
                # DESTAQUE CLARO DO DECISOR RESPONSÁVEL
                resp_nome = top_obra.get('responsavel_nome') or 'Por identificar'
                resp_cargo = top_obra.get('responsavel_cargo') or 'Cargo N/D'
                resp_emp = top_obra.get('responsavel_empresa') or 'Empresa N/D'
                resp_ct = top_obra.get('responsavel_contacto') or 'Contacto a apurar'
                st.markdown(f"""
                <div style="background:#FFF5F5; border-left:4px solid #CC2229; padding:10px 14px; border-radius:6px; margin:10px 0;">
                    <span style="font-weight:700; color:#991B1B;">👤 Decisor Responsável Identificado:</span>
                    <span style="font-weight:700; color:#1E293B;"> {resp_nome}</span> — 
                    <span style="color:#475569;"><i>{resp_cargo}</i> (<b>{resp_emp}</b>)</span>
                    <br><span style="font-size:0.85rem; color:#64748B;">📞 Contacto direto: <b>{resp_ct}</b></span>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"**Resumo:** {top_obra['resumo']}")

                # Empresas envolvidas
                if top_detalhes and top_detalhes.get('empresas'):
                    emps_txt = " • ".join([f"**{e['papel']}:** {e['nome']}" for e in top_detalhes['empresas']])
                    st.markdown(f"**Empresas Identificadas:** {emps_txt}")
                else:
                    st.markdown("**Empresas:** Promotor identificado; Instalador e Projetista por confirmar.")

                # Produtos recomendados
                if top_detalhes and top_detalhes.get('produtos'):
                    prods_txt = ", ".join([p['familia_produto'].split('(')[0].strip() for p in top_detalhes['produtos'][:3]])
                    st.markdown(f"**Potencial PÉMSA:** `{prods_txt}` e acessórios de fixação.")

                st.info(f"👉 **Próxima Ação Comercial:** {top_obra['proxima_acao']}")

            with col_top_score:
                st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
                st.metric("Pontuação PÉMSA", f"{top_obra['score']}/100", f"Prioridade {top_obra['prioridade']}")
                st.caption(f"Valor Est.: {top_obra['valor_estimado'] or 'Sob Consulta'}")
                if st.button("Ver Dossiê Completo ➡️", key="btn_top_detalhe"):
                    st.session_state["obra_selecionada_id"] = top_obra['id']
                    st.info("Aceda ao menu '4. Ficha da Obra' para ver o dossiê detalhado.")
                st.markdown("</div>", unsafe_allow_html=True)

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
    st.markdown('<div class="sub-header">Pesquisa avançada, segmentação geográfica e qualificação comercial</div>', unsafe_allow_html=True)

    # Barra de Filtros
    with st.expander("🛠️ Filtros de Pesquisa e Segmentação", expanded=True):
        fcol1, fcol2, fcol3, fcol4 = st.columns(4)
        with fcol1:
            filtro_segmento = st.selectbox("Segmento de Obra:", [
                "Todos", "Data Center", "Hospital / Saúde", "Industrial / Fábricas",
                "Logística / Armazéns", "Hotel / Turismo", "Energia / Renováveis", "Edifícios Terciários & Públicos"
            ])
        with fcol2:
            filtro_regiao = st.selectbox("Região:", ["Todas", "Norte", "Centro", "Sul", "Madeira", "Açores"])
        with fcol3:
            filtro_fase = st.selectbox("Fase da Obra:", [
                "Todas", "Projeto de Execução / MEP", "Concurso de Empreitada",
                "Início de Construção", "Em Obra (Instalações a decorrer)"
            ])
        with fcol4:
            filtro_prioridade = st.selectbox("Prioridade Comercial:", ["Todas", "Alta", "Média", "Baixa"])

        busca_texto = st.text_input("🔍 Pesquisar por palavra-chave, nome da obra, concelho ou empresa:", "")

    # Obter Obras Filtradas
    obras_filtradas = listar_obras(
        segmento=filtro_segmento,
        regiao=filtro_regiao,
        fase=filtro_fase,
        prioridade=filtro_prioridade,
        busca=busca_texto if busca_texto else None
    )

    st.write(f"Encontradas **{len(obras_filtradas)}** obras correspondentes aos critérios.")

    # Modo de Exibição
    tab_cards, tab_tabela = st.tabs(["🗂️ Vista de Cartões Comerciais", "📊 Vista de Tabela Estruturada"])

    with tab_cards:
        if not obras_filtradas:
            st.info("Nenhuma obra encontrada para estes filtros.")
        for obra in obras_filtradas:
            with st.container(border=True):
                c_info, c_score, c_btn = st.columns([3.5, 1.2, 1])

                with c_info:
                    # Badges
                    badge_class = "badge-alta" if obra['score'] >= 75 else ("badge-media" if obra['score'] >= 50 else "badge-baixa")
                    st.markdown(f"#### {obra['titulo']}")
                    st.markdown(f"""
                    <span class="{badge_class}">Prioridade {obra['prioridade']} ({obra['score']}/100)</span>
                    <span style="background:#EEF2F6; color:#1E293B; padding:3px 8px; border-radius:5px; font-size:0.8rem; margin-left:6px;">📍 {obra['concelho']}, {obra['distrito']}</span>
                    <span style="background:#EEF2F6; color:#1E293B; padding:3px 8px; border-radius:5px; font-size:0.8rem; margin-left:6px;">🏗️ {obra['segmento']}</span>
                    <span style="background:#F0FDF4; color:#15803D; padding:3px 8px; border-radius:5px; font-size:0.8rem; margin-left:6px;">⏱️ {obra['fase']}</span>
                    """, unsafe_allow_html=True)

                    st.markdown(f"<p style='color:#475569; margin-top:8px;'>{obra['resumo']}</p>", unsafe_allow_html=True)

                    # Destaque do Decisor Responsável
                    r_nome = obra.get('responsavel_nome') or 'Por identificar'
                    r_cargo = obra.get('responsavel_cargo') or 'Cargo N/D'
                    r_emp = obra.get('responsavel_empresa') or 'Empresa N/D'
                    r_ct = obra.get('responsavel_contacto') or 'Contacto a apurar'
                    st.markdown(f"""
                    <div style="background:#F8FAFC; border-left:3px solid #CC2229; padding:7px 12px; margin:8px 0; border-radius:4px;">
                        <span style="font-weight:700; color:#1E293B;">👤 Decisor Responsável:</span>
                        <span> <b>{r_nome}</b> — <i>{r_cargo}</i> (<b>{r_emp}</b>)</span>
                        <br><span style="font-size:0.85rem; color:#64748B;">📞 Contacto direto: <b>{r_ct}</b></span>
                    </div>
                    """, unsafe_allow_html=True)

                    st.caption(f"🔗 **Fonte:** {obra['fonte_nome']} | Deteção: {obra['data_detecao']} | Ref: `{obra['codigo_ref']}`")

                with c_score:
                    st.markdown(f"**Timing Fornecimento:**")
                    st.caption(f"{obra['timing_fornecimento']}")
                    st.markdown(f"**Próxima Ação:**")
                    st.caption(f"{obra['proxima_acao']}")

                with c_btn:
                    st.markdown(f"**Estado:** `{obra['status_comercial']}`")
                    if st.button("Abrir Ficha 📄", key=f"btn_ver_{obra['id']}", use_container_width=True):
                        st.session_state["obra_selecionada_id"] = obra['id']
                        st.session_state["navegar_para_ficha"] = True
                        st.info(f"Obra selecionada! Vá a '4. Ficha da Obra' para gerir.")

    with tab_tabela:
        if obras_filtradas:
            df = pd.DataFrame(obras_filtradas)
            colunas_exibir = [
                'id', 'titulo', 'score', 'prioridade',
                'responsavel_nome', 'responsavel_cargo', 'responsavel_empresa', 'responsavel_contacto',
                'segmento', 'distrito', 'regiao', 'fase', 'status_comercial', 'valor_estimado'
            ]
            colunas_presentes = [c for c in colunas_exibir if c in df.columns]
            st.dataframe(df[colunas_presentes], use_container_width=True)

            # Exportação rápida
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

    obras_mapa = listar_obras(regiao=filtro_regiao_global if filtro_regiao_global != "Todas" else None)
    df_mapa = pd.DataFrame(obras_mapa)

    if not df_mapa.empty and 'lat' in df_mapa.columns and 'lon' in df_mapa.columns:
        # Filtrar apenas as que têm coordenadas válidas
        df_geo = df_mapa.dropna(subset=['lat', 'lon']).copy()

        # Legenda explicativa
        col_leg1, col_leg2, col_leg3 = st.columns(3)
        col_leg1.markdown("🟢 **Alta Prioridade (Score >= 75):** Agir Imediatamente")
        col_leg2.markdown("🟡 **Média Prioridade (50 - 74):** Acompanhar Concurso")
        col_leg3.markdown("⚪ **Baixa Prioridade (< 50):** Investigação Passiva")

        # Exibir o mapa interativo
        st.map(df_geo, latitude='lat', longitude='lon', size=25, zoom=6)

        st.markdown("#### Lista de Obras Geolocalizadas:")
        for _, row in df_geo.iterrows():
            with st.expander(f"📍 {row['titulo']} — {row['distrito']} (Score: {row['score']}/100)"):
                st.write(f"**Segmento:** {row['segmento']} | **Fase:** {row['fase']}")
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
    st.markdown('<div class="sub-header">Qualificação 360°, cadeia de decisão e produtos PÉMSA compatíveis</div>', unsafe_allow_html=True)

    todas_obras = listar_obras()
    if not todas_obras:
        st.warning("Nenhuma obra registada na base de dados.")
        st.stop()

    # Seleção de obra
    opcoes_obras = {o['id']: f"[{o['score']} pts] {o['titulo']} ({o['distrito']})" for o in todas_obras}
    obra_id_default = st.session_state.get("obra_selecionada_id", todas_obras[0]['id'])
    # Garantir que o ID existe nas opções
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

        # Cabeçalho Principal da Obra
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown(f"## 🏗️ {obra['titulo']}")
            st.markdown(f"**Referência:** `{obra['codigo_ref']}` | **Segmento:** `{obra['segmento']}` | **Localização:** {obra['morada_localizacao'] or obra['concelho']}, {obra['distrito']} ({obra['regiao']})")
            st.markdown(f"**Fonte Verificável:** [{obra['fonte_nome']}]({obra['fonte_url']}) | Data Deteção: {obra['data_detecao']}")
        with col_h2:
            st.metric("Pontuação PÉMSA", f"{obra['score']}/100", f"Prioridade {obra['prioridade']}")
            st.progress(obra['score'] / 100)

        # DESTAQUE DO DECISOR RESPONSÁVEL PRINCIPAL
        r_nome = obra.get('responsavel_nome') or 'Por identificar'
        r_cargo = obra.get('responsavel_cargo') or 'Cargo N/D'
        r_emp = obra.get('responsavel_empresa') or 'Empresa N/D'
        r_ct = obra.get('responsavel_contacto') or 'Contacto a apurar'
        st.markdown(f"""
        <div style="background:#FFF5F5; border:1px solid #FECACA; border-left:5px solid #CC2229; padding:12px 16px; border-radius:8px; margin: 12px 0;">
            <div style="font-size:0.8rem; font-weight:700; color:#991B1B; text-transform:uppercase; letter-spacing:0.5px;">👤 Pessoa Responsável / Decisor Chave</div>
            <div style="font-size:1.2rem; font-weight:700; color:#1E293B; margin-top:2px;">{r_nome}</div>
            <div style="color:#475569; font-size:0.95rem; margin-top:2px;">
                <b>Cargo:</b> {r_cargo} &nbsp;|&nbsp; <b>Empresa:</b> {r_emp}
            </div>
            <div style="color:#64748B; font-size:0.9rem; margin-top:4px;">
                📞 <b>Contacto Direto:</b> {r_ct}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Atualização do Estado Comercial
        with st.container(border=True):
            col_est1, col_est2 = st.columns([2, 3])
            with col_est1:
                novo_estado = st.selectbox("Estado no Pipeline Comercial:", [
                    "Nova Oportunidade", "Em Qualificação", "Contacto Feito",
                    "Apresentação Técnica Realizada", "Proposta Enviada", "Ganha (Fornecimento Fechado)", "Perdida", "Arquivada"
                ], index=["Nova Oportunidade", "Em Qualificação", "Contacto Feito", "Apresentação Técnica Realizada", "Proposta Enviada", "Ganha (Fornecimento Fechado)", "Perdida", "Arquivada"].index(obra['status_comercial']) if obra['status_comercial'] in ["Nova Oportunidade", "Em Qualificação", "Contacto Feito", "Apresentação Técnica Realizada", "Proposta Enviada", "Ganha (Fornecimento Fechado)", "Perdida", "Arquivada"] else 0)
            with col_est2:
                novas_notas = st.text_input("Notas Comerciais:", value=obra.get('notas_comerciais') or "")
            if st.button("💾 Gravar Atualização Comercial"):
                atualizar_status_obra(obra['id'], novo_estado, novas_notas)
                st.success("Estado e notas atualizados!")
                st.rerun()

        # Detalhes em 3 Separadores
        t_scoring, t_empresas, t_produtos, t_tarefas = st.tabs([
            "📊 Pontuação & Justificação Comercial",
            "👥 Cadeia de Decisão & Contactos",
            "⚡ Produtos PÉMSA Recomendados",
            "📅 Tarefas & Histórico"
        ])

        # TAB 1: BREAKDOWN DO SCORE
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
                st.info("Recalcular pontuação comercial para esta obra.")

            st.markdown(f"**Timing de Fornecimento:** {obra['timing_fornecimento']}")
            st.markdown(f"👉 **Ação Prioritária Sugerida:** {obra['proxima_acao']}")

        # TAB 2: CADEIA DE DECISÃO
        with t_empresas:
            st.subheader("Cadeia de Decisão e Empresas Envolvidas")
            st.caption("A prescrição técnica acontece nos projetistas; a compra efetiva é feita pelos instaladores elétricos.")

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
                                st.markdown(f"**{emp['nome']}** (`{emp['tipo']}`)")
                                st.write(f"📍 {emp['cidade']}, {emp['distrito']} | Tel: {emp['telefone']}")
                                st.caption(f"Notas: {emp.get('rel_notas') or emp.get('notas') or 'Sem notas'}")
                            with col_e_contact:
                                # Buscar pessoas de contacto
                                conn = get_connection()
                                cur = conn.cursor()
                                cur.execute("SELECT * FROM contactos WHERE empresa_id = ?", (emp['id'],))
                                cts = cur.fetchall()
                                conn.close()
                                if cts:
                                    st.markdown("**Contactos Identificados:**")
                                    for c in cts:
                                        st.write(f"👤 **{c['nome']}** — *{c['cargo']}*")
                                        st.write(f"📞 {c['telefone']} | ✉️ {c['email']}")
                                else:
                                    st.warning("⚠️ Contactos diretos ainda não mapeados.")
                    else:
                        st.info(f"Nenhuma empresa associada como '{papel}'. Mapear na fase de qualificação.")

        # TAB 3: PRODUTOS PÉMSA
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
                            st.markdown(f"**Classificação:**")
                            st.info(f"{p['nivel_potencial']}")
            else:
                st.info("Ainda não foram adicionados produtos específicos a esta obra.")

        # TAB 4: TAREFAS & HISTÓRICO
        with t_tarefas:
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
        with st.expander(f"🏢 {emp['nome']} — {emp['tipo']} ({emp['cidade']}, {emp['distrito']})"):
            c_e1, c_e2 = st.columns(2)
            with c_e1:
                st.markdown(f"**NIF:** {emp['nif'] or 'N/D'} | **Relação Comercial:** `{emp['nivel_relacionamento']}`")
                st.markdown(f"📞 {emp['telefone']} | ✉️ {emp['email']}")
                st.markdown(f"🌐 [{emp['website']}]({emp['website']})" if emp['website'] else "")
                st.caption(f"Notas: {emp['notas']}")

                if emp.get('obras_participa'):
                    st.markdown("**Obras Associadas:**")
                    for ob in emp['obras_participa']:
                        st.write(f"• [{ob['papel']}] {ob['titulo']}")

            with c_e2:
                st.markdown("##### 👤 Pessoas de Contacto Mapeadas")
                if emp.get('contactos'):
                    for ct in emp['contactos']:
                        with st.container(border=True):
                            st.markdown(f"**{ct['nome']}** — *{ct['cargo']}*")
                            st.caption(f"Departamento: {ct['departamento'] or 'Geral'}")
                            st.write(f"📞 {ct['telefone']} | ✉️ {ct['email']}")
                            if ct['linkedin']:
                                st.markdown(f"[Perfil LinkedIn]({ct['linkedin']})")
                else:
                    st.info("Ainda sem contactos pessoais registados para esta empresa.")

# =====================================================================
# 6. PLANO COMERCIAL & TAREFAS
# =====================================================================
elif "6. Plano Comercial" in menu_opcao:
    st.markdown('<div class="main-header">📅 Plano Comercial & Ações de Seguimento</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Gestão de contactos, prazos e histórico de prospeção pessoal</div>', unsafe_allow_html=True)

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
                cor_borda = "#EF4444" if is_atr else ("#F59E0B" if is_hj else "#3B82F6")

                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"#### {'🔴 [EM ATRASO] ' if is_atr else ('🟡 [HOJE] ' if is_hj else '🔵 ')}{t['titulo']}")
                        st.write(f"🏗️ **Obra:** {t.get('obra_titulo', 'Geral')} (Score {t.get('obra_score')})")
                        st.write(f"🏢 **Empresa:** {t.get('empresa_nome', 'N/D')} | 👤 **Contacto:** {t.get('contacto_nome', 'N/D')} ({t.get('contacto_telefone', '')})")
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
    st.markdown('<div class="main-header">📡 Motor de Recolha, Alertas & Exportação</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Fontes públicas (Portal BASE, TED, Notícias), Análise com IA e Exportação para Excel</div>', unsafe_allow_html=True)

    tab_alertas, tab_estrategia, tab_ia, tab_freq, tab_excel = st.tabs([
        "🔔 Alertas Recentes das 5 Fontes",
        "🎯 Matriz Estratégica das Fontes (SIAIA, BASE, TED)",
        "🤖 Inserir / Analisar Texto de Obra com IA",
        "⏰ Frequência de Atualização & Automação",
        "📑 Exportar para Excel / Relatório"
    ])

    # SUBTAB 1: ALERTAS DE RECOLHA
    with tab_alertas:
        col_al_top1, col_al_top2 = st.columns([3, 1])
        with col_al_top1:
            st.markdown("##### Feeds Rastreados: Portal BASE, TED Europa, SIAIA / PARTICIPA e Imprensa")
        with col_al_top2:
            if st.button("🔄 Executar Pesquisa Agora", use_container_width=True):
                # Simula nova recolha
                from scrapers import simular_rastreio_alertas
                novos = simular_rastreio_alertas()
                conn = get_connection()
                cur = conn.cursor()
                for n in novos:
                    cur.execute("""
                        INSERT INTO alertas_recolha (fonte_tipo, fonte_nome, titulo, link, data_publicacao, entidade_promotora, resumo_bruto, segmento_estimado, regiao_estimada, processado)
                        VALUES (:fonte_tipo, :fonte_nome, :titulo, :link, :data_publicacao, :entidade_promotora, :resumo_bruto, :segmento_estimado, :regiao_estimada, 0)
                    """, n)
                conn.commit()
                conn.close()
                st.success("Novos alertas obtidos das fontes públicas!")
                st.rerun()

        alertas = listar_alertas(apenas_nao_processados=True)
        st.write(f"Alertas pendentes de aprovação comercial: **{len(alertas)}**")

        for al in alertas:
            with st.container(border=True):
                c_a1, c_a2 = st.columns([3.5, 1])
                with c_a1:
                    st.markdown(f"#### 📢 {al['titulo']}")
                    st.caption(f"Fonte: **{al['fonte_nome']}** ({al['fonte_tipo']}) | Publicado em: {al['data_publicacao']}")
                    st.markdown(f"**Promotor:** {al['entidade_promotora']} | **Segmento:** `{al['segmento_estimado']}` | **Região:** `{al['regiao_estimada']}`")
                    st.write(al['resumo_bruto'])
                    if al['link']:
                        st.markdown(f"[Ver Anúncio Oficial Original]({al['link']})")
                with c_a2:
                    if st.button("Aprovar e Criar Obra ➕", key=f"btn_aprov_{al['id']}", use_container_width=True):
                        # Analisar e converter em obra
                        dados_extraidos = analisar_texto_obra(al['titulo'] + ". " + al['resumo_bruto'], fonte_nome=al['fonte_nome'], fonte_url=al['link'])

                        nova_obra_dict = {
                            "titulo": dados_extraidos["titulo"],
                            "codigo_ref": f"PEMSA-AUTO-{al['id']}",
                            "segmento": dados_extraidos["segmento"],
                            "regiao": dados_extraidos["regiao"],
                            "distrito": dados_extraidos["distrito"],
                            "concelho": dados_extraidos["distrito"],
                            "morada_localizacao": f"{dados_extraidos['distrito']}, Portugal",
                            "lat": 41.15 if dados_extraidos["regiao"] == "Norte" else 38.72,
                            "lon": -8.61 if dados_extraidos["regiao"] == "Norte" else -9.14,
                            "fase": dados_extraidos["fase"],
                            "status_comercial": "Nova Oportunidade",
                            "score": dados_extraidos["score"],
                            "score_breakdown": json.dumps(dados_extraidos["score_breakdown"], ensure_ascii=False),
                            "prioridade": dados_extraidos["prioridade"],
                            "valor_estimado": "Sob Avaliação",
                            "prazo_previsto": "2026 - 2027",
                            "data_detecao": date.today().isoformat(),
                            "fonte_tipo": al["fonte_tipo"],
                            "fonte_nome": al["fonte_nome"],
                            "fonte_url": al["link"],
                            "resumo": dados_extraidos["resumo"],
                            "timing_fornecimento": dados_extraidos["timing_fornecimento"],
                            "proxima_acao": dados_extraidos["proxima_acao"],
                            "notas_comerciais": "Importado automaticamente do feed de alertas públicos.",
                            "responsavel_nome": dados_extraidos.get("responsavel_nome"),
                            "responsavel_cargo": dados_extraidos.get("responsavel_cargo"),
                            "responsavel_empresa": dados_extraidos.get("responsavel_empresa"),
                            "responsavel_contacto": dados_extraidos.get("responsavel_contacto")
                        }

                        # Inserir
                        nova_id = inserir_obra(nova_obra_dict, produtos_pemsa=dados_extraidos["produtos_sugeridos"])
                        marcar_alerta_processado(al['id'], obra_id=nova_id)
                        st.success(f"Obra adicionada com sucesso ao Radar! (ID: {nova_id})")
                        st.rerun()

                    if st.button("Descartar ❌", key=f"btn_desc_{al['id']}", use_container_width=True):
                        marcar_alerta_processado(al['id'], obra_id=None)
                        st.rerun()

    # SUBTAB 2: MATRIZ ESTRATÉGICA DAS FONTES (SIAIA, BASE, TED, NOTÍCIAS)
    with tab_estrategia:
        st.markdown("##### 🎯 Matriz Estratégica das 5 Fontes de Informação PÉMSA")
        st.caption("Como combinar fontes oficiais, ambientais e privadas para descobrir obras antes dos concorrentes.")

        # Os 3 momentos da venda PÉMSA
        st.markdown("""
        <div style="background:linear-gradient(90deg, #F8FAFC 0%, #EFF6FF 100%); border-left:4px solid #CC2229; padding:12px 16px; border-radius:6px; margin-bottom:16px;">
            <b style="color:#CC2229; font-size:1.05rem;">A Regra de Ouro PÉMSA: Não depender apenas de notícias nem de obras já adjudicadas.</b><br>
            <span style="color:#334155; font-size:0.92rem;">
            Se esperarmos pelo <b>Portal BASE</b>, a obra já foi adjudicada e as marcas de caminhos de cabos já foram orçamentadas pelo empreiteiro.<br>
            A grande vitória comercial da PÉMSA é antecipar a abordagem através do <b>SIAIA / PARTICIPA</b> (quando os projetos ainda estão em fase de avaliação ambiental e engenharia) e acompanhar até à contratação final.
            </span>
        </div>
        """, unsafe_allow_html=True)

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            with st.container(border=True):
                st.markdown("#### 1. 🌿 SIAIA (APA) & PARTICIPA")
                st.markdown("*(Agência Portuguesa do Ambiente · siaia.apambiente.pt / participa.pt)*")
                st.markdown("""
                - **Momento Temporal:** **6 a 18 meses ANTES da obra física.**
                - **Tipo de Obra:** Centros de dados (Data Centers), parques industriais, centrais solares com subestações, logística pesada, hospitais.
                - **Documentos Chave:** Resumo Não Técnico (RNT) e Estudos de Impacte Ambiental (AIA).
                - **Interveniente Identificado:** Promotor + Gabinete de Engenharia Projetista (ex: Afaconsult, Quadrante, Proman, Engexpor).
                - **Missão Comercial PÉMSA:** **Prescrição Técnica.** Contactar o projetista MEP para especificar *Rejiband Rapide* (varão) e *Pemsaband* (chapa) no Caderno de Encargos com suporte BIM e ensaios de fogo E90.
                """)

            with st.container(border=True):
                st.markdown("#### 2. 🇪🇺 TED — Tenders Electronic Daily")
                st.markdown("*(União Europeia · ted.europa.eu)*")
                st.markdown("""
                - **Momento Temporal:** **15 a 45 dias antes do encerramento de propostas.**
                - **Tipo de Obra:** Empreitadas públicas de grande valor (> 5,5M€) em Portugal.
                - **Documentos Chave:** Anúncio de concurso público e Caderno de Encargos de instalações elétricas (CPV `45310000`).
                - **Interveniente Identificado:** Entidade Adjudicante + Concorrentes habilitados.
                - **Missão Comercial PÉMSA:** **Cotação em Concurso.** Fornecer cotações rápidas e competitivas aos orçamentistas dos instaladores que vão a concurso, garantindo que concorrem com solução PÉMSA via distribuidores.
                """)

            with st.container(border=True):
                st.markdown("#### 3. 🏛️ Portal BASE")
                st.markdown("*(Contratos Públicos · base.gov.pt)*")
                st.markdown("""
                - **Momento Temporal:** **No dia da adjudicação (0 a 2 meses antes do início de trabalhos).**
                - **Tipo de Obra:** Todas as empreitadas públicas adjudicadas pelo Estado, Câmaras e ULS.
                - **Documentos Chave:** Contrato formal, valor adjudicado, prazo de execução e consórcios.
                - **Interveniente Identificado:** Empreiteiro Geral Vencedor e Instalador Subcontratado.
                - **Missão Comercial PÉMSA:** **Fecho de Fornecimento.** Contactar o Diretor de Obra e o instalador elétrico para canalizar os pedidos através dos distribuidores autorizados PÉMSA (Rexel, Sonepar, etc.).
                """)

        with col_f2:
            with st.container(border=True):
                st.markdown("#### 4. 📰 Imprensa Económica & Setorial")
                st.markdown("*(Jornal de Negócios, Jornal Económico, ECO, Construir)*")
                st.markdown("""
                - **Momento Temporal:** **Fase de Anúncio / Estudo Prévio de Investimento Privado.**
                - **Tipo de Obra:** **Obras 100% Privadas** (novas fábricas, expansões industriais, plataformas logísticas e hotéis que NÃO aparecem no BASE nem no TED).
                - **Documentos Chave:** Notícias de investimento, conferências e comunicados de promotores.
                - **Interveniente Identificado:** Promotor / Grupo Internacional / Autarquia de acolhimento.
                - **Missão Comercial PÉMSA:** **Deteção Precoce.** Descobrir qual o gabinete de arquitetura/engenharia responsável pelo licenciamento e iniciar o contacto de pré-prescrição.
                """)

            with st.container(border=True):
                st.markdown("#### 5. 🏢 Páginas Oficiais das Empresas & Decisores")
                st.markdown("*(Promotores, Gabinetes de Engenharia, Instaladores Elétricos)*")
                st.markdown("""
                - **Momento Temporal:** **Contínuo / Enriquecimento de Dados.**
                - **Tipo de Obra:** Acompanhamento do portfólio de engenharia e obras em carteira.
                - **Documentos Chave:** Portfólios de referências, organigramas e comunicados de imprensa.
                - **Interveniente Identificado:** Diretores de Instalações, Coordenadores MEP, Responsáveis de Compras.
                - **Missão Comercial PÉMSA:** **Qualificação de Contactos.** Validar nomes e cargos técnicos (cruzando com LinkedIn) para transformar o radar numa ação comercial prática (telefonema / reunião / visita).
                """)

            with st.container(border=True):
                st.markdown("#### 🔍 Gerador de Pesquisas Booleanas Automáticas")
                st.caption("Gere filtros prontos para Google Notícias, RSS ou alertas automáticos:")
                
                seg_sel = st.selectbox("Selecione o Segmento:", ["Data Center", "Industrial / Fábricas", "Logística / Armazéns", "Hospital / Saúde", "Energia / Renováveis"])
                reg_sel = st.selectbox("Selecione a Região:", ["Portugal Global", "Norte (Porto, Braga, Famalicão)", "Centro (Aveiro, Coimbra, Leiria)", "Sul (Lisboa, Sines, Setúbal)"])

                if seg_sel == "Data Center":
                    termos_seg = '("data center" OR "centro de dados" OR "campus de dados")'
                elif seg_sel == "Industrial / Fábricas":
                    termos_seg = '("nova fábrica" OR "ampliação industrial" OR "unidade de produção" OR "nova nave industrial")'
                elif seg_sel == "Logística / Armazéns":
                    termos_seg = '("parque logístico" OR "plataforma logística" OR "armazém" OR "centro de distribuição")'
                elif seg_sel == "Hospital / Saúde":
                    termos_seg = '("novo hospital" OR "centro hospitalar" OR "unidade de saúde" OR "ampliação hospitalar")'
                else:
                    termos_seg = '("central solar" OR "parque solar" OR "subestação elétrica" OR "armazenamento de baterias")'

                if "Norte" in reg_sel:
                    termos_reg = 'AND (Porto OR Braga OR Famalicão OR Guimarães OR "Santo Tirso" OR "Vila Real")'
                elif "Centro" in reg_sel:
                    termos_reg = 'AND (Aveiro OR Coimbra OR Leiria OR Viseu OR "Castanheira do Ribatejo" OR Azambuja)'
                elif "Sul" in reg_sel:
                    termos_reg = 'AND (Lisboa OR Sines OR Palmela OR Setúbal OR Oeiras OR Loures OR Évora)'
                else:
                    termos_reg = 'AND (Portugal OR Norte OR Centro OR Alentejo OR Algarve)'

                query_final = f'{termos_seg} {termos_reg}'
                st.code(query_final, language="text")
                st.caption("Copie esta linha para configurar alertas no Google Notícias, Feedly ou alimentar o motor do Radar.")

    # SUBTAB 3: ANALISAR COM IA
    with tab_ia:
        st.markdown("##### 🤖 Importação Rápida Assistida por IA")
        st.caption("Cole aqui o texto de uma notícia, edital do Portal BASE ou anúncio de obra. O motor extrai entidades, empresas, produtos PÉMSA compatíveis e calcula a pontuação comercial.")

        texto_input = st.text_area(
            "Cole o texto da notícia ou anúncio de concurso:",
            height=160,
            value="Construção do novo Parque de Logística e Armazenagem no Carregado com 30.000 m2. Promovido pelo Grupo Lusitânia Logística, o projeto de instalações elétricas MEP foi adjudicado ao gabinete Quadrante Engenharia sob a coordenação do Eng. Tiago Mendonça. Empreitada em fase de projeto de execução com concurso a abrir em breve para empreiteiro e instaladores."
        )

        if st.button("🔍 Analisar e Extrair Inteligência Comercial", use_container_width=True):
            analise = analisar_texto_obra(texto_input)
            st.session_state["ultima_analise_ia"] = analise

        if "ultima_analise_ia" in st.session_state:
            res_ia = st.session_state["ultima_analise_ia"]
            st.success("Análise concluída com sucesso!")

            with st.container(border=True):
                col_r1, col_r2 = st.columns([3, 1])
                with col_r1:
                    st.markdown(f"### 📍 {res_ia['titulo']}")
                    st.write(f"**Segmento:** `{res_ia['segmento']}` | **Região:** `{res_ia['regiao']}` ({res_ia['distrito']}) | **Fase:** `{res_ia['fase']}`")
                    
                    # Mostrar responsável detetado
                    st.markdown(f"""
                    <div style="background:#F8FAFC; border-left:3px solid #CC2229; padding:6px 12px; margin:6px 0; border-radius:4px;">
                        <b>👤 Decisor Detetado:</b> {res_ia.get('responsavel_nome')} — <i>{res_ia.get('responsavel_cargo')}</i> ({res_ia.get('responsavel_empresa')})
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.write(f"**Timing:** {res_ia['timing_fornecimento']}")
                    st.info(f"👉 **Próxima Ação Sugerida:** {res_ia['proxima_acao']}")

                    st.markdown("**Produtos PÉMSA Detetados:**")
                    for p in res_ia['produtos_sugeridos']:
                        st.write(f"• **{p['familia_produto']}** ({p['nivel_potencial']}) — *{p['especificacao_detalhe']}*")

                with col_r2:
                    st.metric("Pontuação Estimada", f"{res_ia['score']}/100", f"Prioridade {res_ia['prioridade']}")

                    if st.button("💾 Gravar no Radar de Obras", key="btn_save_ia_obra", use_container_width=True):
                        nova_obra_dict = {
                            "titulo": res_ia["titulo"],
                            "codigo_ref": f"PEMSA-IA-{datetime.now().strftime('%m%d%H%M')}",
                            "segmento": res_ia["segmento"],
                            "regiao": res_ia["regiao"],
                            "distrito": res_ia["distrito"],
                            "concelho": res_ia["distrito"],
                            "morada_localizacao": f"{res_ia['distrito']}, Portugal",
                            "lat": 41.15 if res_ia["regiao"] == "Norte" else 38.72,
                            "lon": -8.61 if res_ia["regiao"] == "Norte" else -9.14,
                            "fase": res_ia["fase"],
                            "status_comercial": "Nova Oportunidade",
                            "score": res_ia["score"],
                            "score_breakdown": json.dumps(res_ia["score_breakdown"], ensure_ascii=False),
                            "prioridade": res_ia["prioridade"],
                            "valor_estimado": "Sob Consulta",
                            "prazo_previsto": "2026 - 2027",
                            "data_detecao": date.today().isoformat(),
                            "fonte_tipo": "Extração Assistida IA",
                            "fonte_nome": "Notícia / Documento Colado",
                            "fonte_url": "",
                            "resumo": res_ia["resumo"],
                            "timing_fornecimento": res_ia["timing_fornecimento"],
                            "proxima_acao": res_ia["proxima_acao"],
                            "notas_comerciais": "Importado via assistente IA.",
                            "responsavel_nome": res_ia.get("responsavel_nome"),
                            "responsavel_cargo": res_ia.get("responsavel_cargo"),
                            "responsavel_empresa": res_ia.get("responsavel_empresa"),
                            "responsavel_contacto": res_ia.get("responsavel_contacto")
                        }
                        nova_id = inserir_obra(nova_obra_dict, produtos_pemsa=res_ia["produtos_sugeridos"])
                        st.success(f"Obra gravada no Radar com ID {nova_id}!")
                        st.rerun()

    # SUBTAB 3: FREQUÊNCIA DE ATUALIZAÇÃO & AUTOMAÇÃO
    with tab_freq:
        st.markdown("##### ⏰ De quanto em quanto tempo o Radar atualiza com novas obras?")
        st.caption("Estratégia de sincronização e periodicidade recomendada para o mercado da construção em Portugal.")

        with st.container(border=True):
            col_fq1, col_fq2 = st.columns([2, 1])
            with col_fq1:
                st.markdown("### 📅 Periodicidade Recomendada: **Semanal (Segundas às 08:00)**")
                st.markdown("""
                No mercado de construção em Portugal, as empreitadas públicas e privadas não mudam minuto a minuto:
                - **Portal BASE & Concursos**: Os anúncios têm prazos legais de candidatura de **15 a 45 dias**.
                - **Projetos de Execução / MEP**: A fase de especificação das engenharias dura semanas ou meses.
                - **Grandes Investimentos**: Notícias de novos parques e fábricas surgem em blocos semanais.
                
                **Porquê Segunda-feira de manhã?**
                Permite à equipa comercial começar a semana com o painel renovado:
                - Novas obras detetadas no fim de semana e na semana anterior;
                - Mapeamento imediato de quem contactar nos próximos 5 dias úteis;
                - Seguimento prioritário antes dos instaladores fecharem as compras de material elétrico.
                """)
            with col_fq2:
                st.markdown("#### ⚙️ Configuração Ativa")
                freq_escolhida = st.radio(
                    "Selecione o Ritmo de Sincronização:",
                    [
                        "Semanal (Segunda-feira às 08:00) — Recomendado",
                        "Diária (Dias úteis às 07:30)",
                        "Manual (Apenas quando solicito pesquisa)"
                    ],
                    index=0
                )
                st.success(f"Configuração guardada: `{freq_escolhida.split('—')[0].strip()}`")
                st.caption(f"Última verificação: **{date.today().isoformat()} às 08:00**")

        st.markdown("---")
        st.markdown("#### 🔄 Modos de Atualização Disponíveis:")
        c_m1, c_m2, c_m3 = st.columns(3)
        with c_m1:
            st.markdown("##### 1. Sob Demanda (Instantâneo)")
            st.write("Basta carregar no botão **'🔄 Executar Pesquisa Agora'** na aba de alertas para importar e analisar imediatamente novas fontes.")
        with c_m2:
            st.markdown("##### 2. Diária Automática")
            st.write("Rastreia todas as manhãs às 07:30 os novos contratos de empreitada publicados no Diário da República e no Portal BASE no dia útil anterior.")
        with c_m3:
            st.markdown("##### 3. Semanal Consolidada")
            st.write("Consolida todas as notícias económicas, atas de licenciamento municipal e editais para gerar o resumo de oportunidades de segunda-feira.")

    # SUBTAB 4: EXPORTAÇÃO EXCEL
    with tab_excel:
        st.markdown("##### 📑 Exportação de Relatório Comercial Completo")
        st.write("Exporte todas as oportunidades qualificadas, scores, empresas e contactos para uma folha de cálculo Excel (.xlsx).")

        obras_exp = listar_obras()
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
            st.success("Ficheiro Excel preparado com sucesso!")
        else:
            st.info("Sem dados para exportar.")
