"""
scrapers.py - Motor de recolha, conectores de dados públicos e interpretador inteligente.
Simula e integra feeds do Portal BASE, TED e notícias de obras em Portugal.
"""

import re
from datetime import datetime, date
from pemsa_catalog import avaliar_compatibilidade_pemsa
from scoring import calcular_score_obra

# Dicionário de distritos e regiões de Portugal
REGIOES_PORTUGAL = {
    "Norte": ["Viana do Castelo", "Braga", "Porto", "Vila Real", "Bragança"],
    "Centro": ["Aveiro", "Viseu", "Guarda", "Coimbra", "Castelo Branco", "Leiria"],
    "Sul": ["Lisboa", "Santarém", "Setúbal", "Portalegre", "Évora", "Beja", "Faro"],
    "Madeira": ["Madeira", "Funchal"],
    "Açores": ["Açores", "Ponta Delgada", "Angra do Heroísmo"]
}

def identificar_regiao_distrito(texto):
    """Identifica distrito e região de Portugal a partir do texto."""
    texto_lower = texto.lower()
    for regiao, distritos in REGIOES_PORTUGAL.items():
        for dist in distritos:
            if dist.lower() in texto_lower:
                return regiao, dist
    # Concelhos comuns
    concelhos_norte = ["famalicão", "guimarães", "maia", "matosinhos", "gaia", "santo tirso", "trofa"]
    concelhos_sul = ["sines", "cascais", "sintra", "oeiras", "loures", "palmela", "seixal", "benavente"]
    concelhos_centro = ["azambuja", "castanheira", "íhavo", "águada", "mealhada", "pombal"]

    for c in concelhos_norte:
        if c in texto_lower:
            return "Norte", "Porto" if c in ["maia", "matosinhos", "gaia"] else "Braga"
    for c in concelhos_sul:
        if c in texto_lower:
            return "Sul", "Setúbal" if c in ["sines", "palmela", "seixal"] else "Lisboa"
    for c in concelhos_centro:
        if c in texto_lower:
            return "Centro", "Lisboa" if c in ["azambuja", "castanheira"] else "Aveiro"

    return "Norte", "Porto"

def identificar_segmento(texto):
    """Deteta o segmento de construção a partir do texto."""
    t = texto.lower()
    if any(k in t for k in ["data center", "centro de dados", "campus digital", "sines 4.0"]):
        return "Data Center"
    if any(k in t for k in ["hospital", "centro hospitalar", "unidade de saúde", "clínica", "cuidados"]):
        return "Hospital / Saúde"
    if any(k in t for k in ["fábrica", "industrial", "indústria", "produção", "ampliação fabril", "unidade fabril"]):
        return "Industrial / Fábricas"
    if any(k in t for k in ["logística", "parque logístico", "armazém", "plataforma logística", "centro de distribuição"]):
        return "Logística / Armazéns"
    if any(k in t for k in ["hotel", "resort", "empreendimento turístico", "alojamento turístico"]):
        return "Hotel / Turismo"
    if any(k in t for k in ["fotovoltaico", "solar", "eólico", "subestação", "hidrogénio", "baterias"]):
        return "Energia / Renováveis"
    return "Edifícios Terciários & Públicos"

def identificar_fase(texto):
    """Estima a fase da obra a partir dos termos técnicos."""
    t = texto.lower()
    if any(k in t for k in ["estudo prévio", "licenciamento", "pedido de viabilidade", "projeto de execução", "em fase de projeto"]):
        return "Projeto de Execução / MEP"
    if any(k in t for k in ["abertura de concurso", "concurso público", "lançamento de empreitada", "em consulta"]):
        return "Concurso de Empreitada"
    if any(k in t for k in ["adjudicado", "adjudicação da empreitada", "consignação"]):
        return "Adjudicação / Pré-Construção"
    if any(k in t for k in ["primeira pedra", "início das obras", "estaleiro montado", "início de construção"]):
        return "Início de Construção"
    if any(k in t for k in ["em construção", "trabalhos em curso", "fase de betão", "montagem de instalações"]):
        return "Em Obra (Instalações a decorrer)"
    return "Projeto de Execução / MEP"

def analisar_texto_obra(texto_livre, fonte_nome="Inserção / Pesquisa", fonte_url=""):
    """
    Motor inteligente de IA/Regras que extrai entidades e parâmetros comerciais
    de um texto de notícia, anúncio do Portal BASE ou edital do TED.
    """
    segmento = identificar_segmento(texto_livre)
    regiao, distrito = identificar_regiao_distrito(texto_livre)
    fase = identificar_fase(texto_livre)

    # Identificar se há menção a empresas
    papeis_identificados = []
    empresas_sugeridas = []

    # Extração de padrões de promotores ou instaladores
    promotor_match = re.search(r'(?:promovido por|promotor|dono de obra|investimento da|empresa|grupo)\s+([A-ZÀ-Ú][a-zA-ZÀ-ú0-9\s&]+?)(?:,|\.|\be\b|\bque\b|\bpara\b|\bno\b)', texto_livre)
    if promotor_match:
        nome_promotor = promotor_match.group(1).strip()
        if len(nome_promotor) > 3 and len(nome_promotor) < 50:
            empresas_sugeridas.append({"nome": nome_promotor, "papel": "Promotor/Dono", "tipo": "Promotor"})
            papeis_identificados.append("Promotor/Dono")

    projetista_match = re.search(r'(?:projeto de|engenharia|projetista|gabinete de engenharia)\s+([A-ZÀ-Ú][a-zA-ZÀ-ú0-9\s&]+?)(?:,|\.|\be\b|\bpara\b)', texto_livre)
    if projetista_match:
        nome_proj = projetista_match.group(1).strip()
        if len(nome_proj) > 3 and len(nome_proj) < 50:
            empresas_sugeridas.append({"nome": nome_proj, "papel": "Projetista MEP", "tipo": "Projetista MEP"})
            papeis_identificados.append("Projetista MEP")

    empreiteiro_match = re.search(r'(?:adjudicad[ao] à|empreiteiro|construção a cargo da|consórcio)\s+([A-ZÀ-Ú][a-zA-ZÀ-ú0-9\s&]+?)(?:,|\.|\be\b|\bpor\b)', texto_livre)
    if empreiteiro_match:
        nome_emp = empreiteiro_match.group(1).strip()
        if len(nome_emp) > 3 and len(nome_emp) < 50:
            empresas_sugeridas.append({"nome": nome_emp, "papel": "Empreiteiro Geral", "tipo": "Empreiteiro Geral"})
            papeis_identificados.append("Empreiteiro Geral")

    # Avaliar produtos PÉMSA compatíveis
    produtos = avaliar_compatibilidade_pemsa(segmento, texto_livre)

    # Timing de fornecimento estimado
    if "projeto" in fase.lower() or "concurso" in fase.lower():
        timing = "Especificação técnica em aberto (sem compra fechada)"
    elif "início" in fase.lower():
        timing = "Subempreitada elétrica em consulta / Fase inicial de estrutura"
    else:
        timing = "Obra em andamento - validar fornecedor de material elétrico com urgência"

    # Calcular score de oportunidade
    scoring = calcular_score_obra(
        fase=fase,
        segmento=segmento,
        qtd_produtos_compativeis=len(produtos),
        decisores_identificados=papeis_identificados,
        tem_contactos_diretos=False,
        timing_fornecimento=timing,
        regiao=regiao
    )

    # Próxima ação recomendada pela estratégia comercial PÉMSA
    if "Projetista MEP" in papeis_identificados:
        proxima_acao = f"Contactar o projetista ({empresas_sugeridas[1]['nome'] if len(empresas_sugeridas)>1 else 'gabinete'}) para apresentar especificações e vantagens de {produtos[0]['familia_produto'] if produtos else 'PÉMSA'}."
    elif "Promotor/Dono" in papeis_identificados:
        proxima_acao = "Apurar junto do dono da obra qual o gabinete responsável pelo projeto elétrico (MEP) e a data prevista para consultas."
    elif "Empreiteiro Geral" in papeis_identificados:
        proxima_acao = "Identificar o instalador elétrico subcontratado pelo empreiteiro para cotar o pacote de caminhos de cabos e tubos."
    else:
        proxima_acao = "Investigar intervenientes técnicos no Portal BASE / LinkedIn / Notícias para mapear o projetista elétrico."

    # Extração de pessoa responsável e cargo
    pessoa_match = re.search(r'(?:Eng\.(?:ª)?|Dr\.(?:ª)?|Arqt\.(?:o|a)?|responsável|diretor(?:a)?|coordenador(?:a)?)\s+([A-ZÀ-Ú][a-zA-ZÀ-ú]+(?:\s+[A-ZÀ-Ú][a-zA-ZÀ-ú]+){1,3})', texto_livre)
    if pessoa_match:
        responsavel_nome = pessoa_match.group(0).strip()
        if "projet" in texto_livre.lower():
            responsavel_cargo = "Projetista / Coordenador MEP"
            responsavel_empresa = empresas_sugeridas[1]['nome'] if len(empresas_sugeridas) > 1 else (empresas_sugeridas[0]['nome'] if empresas_sugeridas else "Gabinete de Engenharia")
        else:
            responsavel_cargo = "Diretor de Obra / Instalações"
            responsavel_empresa = empresas_sugeridas[0]['nome'] if empresas_sugeridas else "Empreiteiro / Promotor"
    else:
        if empresas_sugeridas:
            emp = empresas_sugeridas[0]
            responsavel_nome = "Direção Técnica / Gabinete de Compras"
            responsavel_cargo = f"Responsável ({emp['papel']})"
            responsavel_empresa = emp['nome']
        else:
            responsavel_nome = "A Mapear (Decisor Técnico)"
            responsavel_cargo = "Projetista Elétrico MEP"
            responsavel_empresa = "Gabinete por confirmar"

    responsavel_contacto = "Pesquisa no Portal BASE / LinkedIn"

    return {
        "titulo": titulo,
        "segmento": segmento,
        "regiao": regiao,
        "distrito": distrito,
        "fase": fase,
        "timing_fornecimento": timing,
        "score": scoring["score_total"],
        "prioridade": scoring["prioridade"],
        "score_breakdown": scoring,
        "proxima_acao": proxima_acao,
        "produtos_sugeridos": produtos,
        "empresas_sugeridas": empresas_sugeridas,
        "responsavel_nome": responsavel_nome,
        "responsavel_cargo": responsavel_cargo,
        "responsavel_empresa": responsavel_empresa,
        "responsavel_contacto": responsavel_contacto,
        "resumo": texto_livre[:400] + ("..." if len(texto_livre) > 400 else ""),
        "fonte_nome": fonte_nome,
        "fonte_url": fonte_url
    }

def simular_rastreio_alertas():
    """
    Gera um lote de alertas simulados / recolhidos de fontes públicas portuguesas
    (Portal BASE, TED e imprensa económica/industrial) para demonstração de rastreio automático.
    """
    alertas_exemplo = [
        {
            "fonte_tipo": "Portal BASE",
            "fonte_nome": "Base.gov.pt — Contratos Públicos",
            "titulo": "Empreitada de Construção do Novo Centro de Saúde de Gaia Sul e Instalações Especiais",
            "link": "https://www.base.gov.pt/Base4/pt/resultados/?type=contratos",
            "data_publicacao": date.today().isoformat(),
            "entidade_promotora": "Município de Vila Nova de Gaia / ULS Gaia e Espinho",
            "segmento_estimado": "Hospital / Saúde",
            "regiao_estimada": "Norte",
            "resumo_bruto": "Concurso público para construção do novo centro de saúde com lote específico para instalações técnicas de eletricidade, redes de dados e telecomunicações no valor de 2,4M€. Fase: Lançamento de Concurso."
        },
        {
            "fonte_tipo": "TED Europa",
            "fonte_nome": "Tenders Electronic Daily (TED)",
            "titulo": "Portugal-Lisboa: Construção do Novo Pólo Universitário e Laboratórios de Investigação Tecnológica",
            "link": "https://ted.europa.eu/en/notice/-/detail/2026-PT-LABS",
            "data_publicacao": date.today().isoformat(),
            "entidade_promotora": "Universidade de Lisboa",
            "segmento_estimado": "Edifícios Terciários & Públicos",
            "regiao_estimada": "Sul",
            "resumo_bruto": "Aviso de concurso internacional para execução de edifício de laboratórios de física e engenharia com forte exigência de proteção eletromagnética e caminhos de cabos em chapa metálica e varão."
        },
        {
            "fonte_tipo": "Notícias Económicas",
            "fonte_nome": "Jornal de Negócios / Investimento",
            "titulo": "Operador Internacional anuncia novo Data Center verde em Palmela com 40 MW de potência",
            "link": "https://jornaldenegocios.pt/empresas/datacenter-palmela",
            "data_publicacao": date.today().isoformat(),
            "entidade_promotora": "Iberia Data Hubs / Fund Invest",
            "segmento_estimado": "Data Center",
            "regiao_estimada": "Sul",
            "resumo_bruto": "Investimento privado de 120 milhões de euros para início de construção em 2026. Projeto de engenharia MEP a cargo de consórcio ibérico. Elevada necessidade de caminhos de cabos em varão Rejiband para servidores e salas técnicas."
        },
        {
            "fonte_tipo": "Comunicados Industriais",
            "fonte_nome": "AIMMAP / Indústria Norte",
            "titulo": "Expansão da Unidade Fabril de Componentes em Santo Tirso com nova nave de 15.000 m2",
            "link": "https://aimmap.pt/noticias/expansao-st-tirso",
            "data_publicacao": date.today().isoformat(),
            "entidade_promotora": "MetalTech Portugal Lda",
            "segmento_estimado": "Industrial / Fábricas",
            "regiao_estimada": "Norte",
            "resumo_bruto": "Licenciamento aprovado pela Câmara Municipal. Projeto elétrico em fase final de execução. Oportunidade para caminhos de cabos em chapa pesada e tubos industriais estanques."
        }
    ]
    return alertas_exemplo
