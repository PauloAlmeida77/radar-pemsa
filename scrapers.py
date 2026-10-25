"""
scrapers.py - Motor de recolha, conectores de dados públicos e qualificação baseada em evidência.
Integra feeds reais de notícias económicas/setoriais (RSS), TED Europa (API pública) e portais públicos,
validando respostas HTTP, timeouts, datas reais de publicação e nível de evidência.
"""

import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, date
from email.utils import parsedate_to_datetime
import requests
import urllib3
from pemsa_catalog import avaliar_compatibilidade_pemsa
from scoring import calcular_score_obra

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Dicionário de distritos e regiões de Portugal
REGIOES_PORTUGAL = {
    "Norte": ["Viana do Castelo", "Braga", "Porto", "Vila Real", "Bragança"],
    "Centro": ["Aveiro", "Viseu", "Guarda", "Coimbra", "Castelo Branco", "Leiria"],
    "Sul": ["Lisboa", "Santarém", "Setúbal", "Portalegre", "Évora", "Beja", "Faro"],
    "Madeira": ["Madeira", "Funchal", "Porto Santo"],
    "Açores": ["Açores", "Ponta Delgada", "Angra do Heroísmo", "Horta"]
}

CONCELHOS_MAPA = {
    "famalicão": ("Norte", "Braga", "Vila Nova de Famalicão"),
    "vila nova de famalicão": ("Norte", "Braga", "Vila Nova de Famalicão"),
    "guimarães": ("Norte", "Braga", "Guimarães"),
    "barcelos": ("Norte", "Braga", "Barcelos"),
    "braga": ("Norte", "Braga", "Braga"),
    "maia": ("Norte", "Porto", "Maia"),
    "matosinhos": ("Norte", "Porto", "Matosinhos"),
    "vila nova de gaia": ("Norte", "Porto", "Vila Nova de Gaia"),
    "gaia": ("Norte", "Porto", "Vila Nova de Gaia"),
    "santo tirso": ("Norte", "Porto", "Santo Tirso"),
    "trofa": ("Norte", "Porto", "Trofa"),
    "felgueiras": ("Norte", "Porto", "Felgueiras"),
    "penafiel": ("Norte", "Porto", "Penafiel"),
    "paços de ferreira": ("Norte", "Porto", "Paços de Ferreira"),
    "valongo": ("Norte", "Porto", "Valongo"),
    "porto": ("Norte", "Porto", "Porto"),
    "viana do castelo": ("Norte", "Viana do Castelo", "Viana do Castelo"),
    "vila real": ("Norte", "Vila Real", "Vila Real"),
    "bragança": ("Norte", "Bragança", "Bragança"),
    "aveiro": ("Centro", "Aveiro", "Aveiro"),
    "ílhavo": ("Centro", "Aveiro", "Ílhavo"),
    "águeda": ("Centro", "Aveiro", "Águeda"),
    "santa maria da feira": ("Centro", "Aveiro", "Santa Maria da Feira"),
    "oliveira de azeméis": ("Centro", "Aveiro", "Oliveira de Azeméis"),
    "coimbra": ("Centro", "Coimbra", "Coimbra"),
    "figueira da foz": ("Centro", "Coimbra", "Figueira da Foz"),
    "leiria": ("Centro", "Leiria", "Leiria"),
    "pombal": ("Centro", "Leiria", "Pombal"),
    "alcobaça": ("Centro", "Leiria", "Alcobaça"),
    "viseu": ("Centro", "Viseu", "Viseu"),
    "tondela": ("Centro", "Viseu", "Tondela"),
    "guarda": ("Centro", "Guarda", "Guarda"),
    "castelo branco": ("Centro", "Castelo Branco", "Castelo Branco"),
    "fundão": ("Centro", "Castelo Branco", "Fundão"),
    "covilhã": ("Centro", "Castelo Branco", "Covilhã"),
    "lisboa": ("Sul", "Lisboa", "Lisboa"),
    "sintra": ("Sul", "Lisboa", "Sintra"),
    "cascais": ("Sul", "Lisboa", "Cascais"),
    "oeiras": ("Sul", "Lisboa", "Oeiras"),
    "loures": ("Sul", "Lisboa", "Loures"),
    "amadora": ("Sul", "Lisboa", "Amadora"),
    "odivelas": ("Sul", "Lisboa", "Odivelas"),
    "mafra": ("Sul", "Lisboa", "Mafra"),
    "vila franca de xira": ("Sul", "Lisboa", "Vila Franca de Xira"),
    "póvoa de santa iria": ("Sul", "Lisboa", "Vila Franca de Xira"),
    "castanheira do ribatejo": ("Sul", "Lisboa", "Vila Franca de Xira"),
    "carregado": ("Sul", "Lisboa", "Alenquer"),
    "alenquer": ("Sul", "Lisboa", "Alenquer"),
    "azambuja": ("Sul", "Lisboa", "Azambuja"),
    "santarém": ("Sul", "Santarém", "Santarém"),
    "coruche": ("Sul", "Santarém", "Coruche"),
    "benavente": ("Sul", "Santarém", "Benavente"),
    "entroncamento": ("Sul", "Santarém", "Entroncamento"),
    "torres novas": ("Sul", "Santarém", "Torres Novas"),
    "setúbal": ("Sul", "Setúbal", "Setúbal"),
    "sines": ("Sul", "Setúbal", "Sines"),
    "palmela": ("Sul", "Setúbal", "Palmela"),
    "seixal": ("Sul", "Setúbal", "Seixal"),
    "almada": ("Sul", "Setúbal", "Almada"),
    "barreiro": ("Sul", "Setúbal", "Barreiro"),
    "montijo": ("Sul", "Setúbal", "Montijo"),
    "alcochete": ("Sul", "Setúbal", "Alcochete"),
    "grândola": ("Sul", "Setúbal", "Grândola"),
    "comporta": ("Sul", "Setúbal", "Grândola"),
    "santiago do cacém": ("Sul", "Setúbal", "Santiago do Cacém"),
    "évora": ("Sul", "Évora", "Évora"),
    "beja": ("Sul", "Beja", "Beja"),
    "portalegre": ("Sul", "Portalegre", "Portalegre"),
    "faro": ("Sul", "Faro", "Faro"),
    "loulé": ("Sul", "Faro", "Loulé"),
    "portimão": ("Sul", "Faro", "Portimão"),
    "lagos": ("Sul", "Faro", "Lagos"),
    "funchal": ("Madeira", "Madeira", "Funchal"),
    "madeira": ("Madeira", "Madeira", "Funchal"),
    "ponta delgada": ("Açores", "Açores", "Ponta Delgada"),
    "açores": ("Açores", "Açores", "Ponta Delgada"),
}


def identificar_localizacao_portugal(texto):
    """
    Identifica (regiao, distrito, concelho, localização_confirmada) a partir do texto.
    Nunca inventa 'Porto' se nenhuma localização for detetada no texto: devolve localização_confirmada=False.
    """
    if not texto:
        return "Por verificar", "Por verificar", "Por verificar", False

    texto_lower = texto.lower()
    # Ordenar chaves por comprimento decrescente para detetar 'vila nova de famalicão' antes de 'vila'
    for chave in sorted(CONCELHOS_MAPA.keys(), key=len, reverse=True):
        padrao = r'\b' + re.escape(chave) + r'\b'
        if re.search(padrao, texto_lower):
            reg, dist, conc = CONCELHOS_MAPA[chave]
            return reg, dist, conc, True

    for regiao, distritos in REGIOES_PORTUGAL.items():
        for dist in distritos:
            if re.search(r'\b' + re.escape(dist.lower()) + r'\b', texto_lower):
                return regiao, dist, dist, True

    return "Por verificar", "Por verificar", "Por verificar", False


def identificar_regiao_distrito(texto):
    """Compatibilidade com chamadas legadas que esperam (regiao, distrito)."""
    reg, dist, _, confirmado = identificar_localizacao_portugal(texto)
    if not confirmado:
        return "Por verificar", "Por verificar"
    return reg, dist


def identificar_segmento(texto):
    """Deteta o segmento de construção a partir do texto."""
    t = (texto or "").lower()
    if any(k in t for k in ["data center", "datacenter", "centro de dados", "campus digital", "sines 4.0"]):
        return "Data Center"
    if any(k in t for k in ["hospital", "centro hospitalar", "unidade de saúde", "centro de saúde", "clínica", "urgência"]):
        return "Hospital / Saúde"
    if any(k in t for k in ["fábrica", "unidade fabril", "unidade industrial", "ampliação industrial", "nave industrial", "linha de produção"]):
        return "Industrial / Fábricas"
    if any(k in t for k in ["logística", "parque logístico", "armazém", "plataforma logística", "centro de distribuição", "entreposto"]):
        return "Logística / Armazéns"
    if any(k in t for k in ["hotel", "resort", "unidade hoteleira", "empreendimento turístico", "aparthotel"]):
        return "Hotel / Turismo"
    if any(k in t for k in ["fotovoltaico", "fotovoltaica", "central solar", "parque solar", "parque eólico", "subestação", "hidrogénio", "baterias"]):
        return "Energia / Renováveis"
    return "Edifícios Terciários & Públicos"


def identificar_fase(texto):
    """
    Identifica a fase da obra apenas se houver evidência textual explícita.
    Caso contrário devolve 'Por verificar'.
    """
    t = (texto or "").lower()
    if any(k in t for k in ["estudo prévio", "licenciamento", "avaliação de impacte ambiental", "consulta pública", "siaia", "participa", "projeto de execução", "em fase de projeto"]):
        return "Projeto de Execução / MEP"
    if any(k in t for k in ["abertura de concurso", "concurso público", "lançamento de empreitada", "lança concurso", "concurso para a empreitada", "em consulta"]):
        return "Concurso de Empreitada"
    if any(k in t for k in ["adjudicado", "adjudicada", "adjudicação", "consignação da empreitada", "vence concurso", "ganha empreitada"]):
        return "Adjudicação / Pré-Construção"
    if any(k in t for k in ["primeira pedra", "início das obras", "arranque das obras", "estaleiro", "início de construção"]):
        return "Início de Construção"
    if any(k in t for k in ["em construção", "trabalhos em curso", "obras em curso", "montagem de instalações"]):
        return "Em Obra (Instalações a decorrer)"
    return "Por verificar"


def extrair_valor_estimado(texto):
    """Extrai valor monetário apenas quando explicitamente referido no texto."""
    if not texto:
        return None
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(milhões|milhão|M€|mil\s*euros)', texto, re.IGNORECASE)
    if m:
        num = m.group(1).replace(",", ".")
        unidade = m.group(2).lower()
        if "milh" in unidade or "m€" in unidade:
            return f"{num} M€ (Confirmado por fonte)"
        return f"{m.group(0).strip()} (Confirmado por fonte)"
    m_eur = re.search(r'(\d{1,3}(?:\.\d{3})+(?:,\d{2})?)\s*(?:€|euros)', texto, re.IGNORECASE)
    if m_eur:
        return f"{m_eur.group(1)} € (Confirmado por fonte)"
    return None


def extrair_codigo_oficial(texto):
    """Extrai identificador oficial (ex.: n.º de anúncio DR, processo SIAIA/AIA, concurso ou CPV) se existir."""
    if not texto:
        return None
    padroes = [
        r'(?:Anúncio de procedimento|Procedimento|Concurso Público)\s*n\.º\s*([0-9]+/[0-9]{4})',
        r'(?:Processo AIA|SIAIA)\s*(?:n\.º)?\s*([0-9]{3,6})',
        r'\b(202[4-9]/[A-Z0-9\-]+)\b',
    ]
    for p in padroes:
        m = re.search(p, texto, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def normalizar_data_publicacao(raw_date_str):
    """
    Converte datas RFC 2822 (RSS pubDate) ou ISO 8601 para 'YYYY-MM-DD'.
    Nunca substitui datas inválidas/ausentes pela data de consulta atual (devolve None).
    """
    if not raw_date_str or not str(raw_date_str).strip():
        return None
    s = str(raw_date_str).strip()
    try:
        dt = parsedate_to_datetime(s)
        return dt.date().isoformat()
    except Exception:
        pass
    try:
        # Tentar ISO 8601 (ex: 2026-10-20T14:30:00Z ou 2026-10-20)
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date().isoformat()
    except Exception:
        pass
    m = re.search(r'(\d{4}-\d{2}-\d{2})', s)
    if m:
        return m.group(1)
    return None


def extrair_entidades_verificaveis(texto):
    """
    Extrai apenas empresas ou entidades públicas explicitamente sustentadas pelo texto.
    Nunca inventa nomes de pessoas, emails ou telefones.
    """
    empresas_sugeridas = []
    papeis_identificados = []
    if not texto:
        return empresas_sugeridas, papeis_identificados

    # Entidades públicas / promotores explícitos
    padroes_promotor = [
        r'(?:Câmara Municipal d[eao]s?\s+[A-ZÀ-Ú][a-zA-ZÀ-ú\s\-]+?)(?:,|\.|\blança|\badjudica|\bannonce|\binveste|\bque\b|\bpara\b|$)',
        r'(?:Município d[eao]s?\s+[A-ZÀ-Ú][a-zA-ZÀ-ú\s\-]+?)(?:,|\.|\blança|\badjudica|\binveste|\bque\b|\bpara\b|$)',
        r'(?:Unidade Local de Saúde d[eao]s?\s+[A-ZÀ-Ú][a-zA-ZÀ-ú\s\-]+?)(?:,|\.|\blança|\badjudica|\bque\b|\bpara\b|$)',
        r'(?:promovido por|promotor|dono de obra|investimento da|proponente)\s+([A-ZÀ-Ú][a-zA-ZÀ-ú0-9\s&\.\-]+?)(?:,|\.|\be\b|\bque\b|\bpara\b|\bno\b|\bna\b|\bem\b|$)',
    ]
    for pat in padroes_promotor:
        m = re.search(pat, texto)
        if m:
            nome = (m.group(1) if m.lastindex else m.group(0)).strip(" ,.")
            if 3 < len(nome) <= 65:
                empresas_sugeridas.append({
                    "nome": nome,
                    "papel": "Promotor/Dono",
                    "tipo": "Promotor",
                    "estado_verificacao": "Confirmado por fonte"
                })
                papeis_identificados.append("Promotor/Dono")
                break

    projetista_match = re.search(
        r'(?:projeto de arquitetura e engenharia d[ea]|projetista|gabinete de engenharia|projeto adjudicado a|coordenação técnica d[ea])\s+([A-ZÀ-Ú][a-zA-ZÀ-ú0-9\s&\.\-]+?)(?:,|\.|\be\b|\bpara\b|\bno\b|$)',
        texto
    )
    if projetista_match:
        nome_proj = projetista_match.group(1).strip(" ,.")
        if 3 < len(nome_proj) <= 65:
            empresas_sugeridas.append({
                "nome": nome_proj,
                "papel": "Projetista MEP",
                "tipo": "Projetista MEP",
                "estado_verificacao": "Confirmado por fonte"
            })
            papeis_identificados.append("Projetista MEP")

    empreiteiro_match = re.search(
        r'(?:adjudicad[ao] à|empreitada entregue à|construído pel[ao]|consórcio liderado pel[ao]|construtora)\s+([A-ZÀ-Ú][a-zA-ZÀ-ú0-9\s&\.\-]+?)(?:,|\.|\be\b|\bpor\b|\bpelo\b|\bno\b|$)',
        texto
    )
    if empreiteiro_match:
        nome_emp = empreiteiro_match.group(1).strip(" ,.")
        if 3 < len(nome_emp) <= 65:
            empresas_sugeridas.append({
                "nome": nome_emp,
                "papel": "Empreiteiro Geral",
                "tipo": "Empreiteiro Geral",
                "estado_verificacao": "Confirmado por fonte"
            })
            papeis_identificados.append("Empreiteiro Geral")

    return empresas_sugeridas, papeis_identificados


def avaliar_evidencia_item(titulo, resumo="", fonte_tipo=""):
    """
    Avalia rigorosamente se uma notícia ou anúncio tem evidência verificável suficiente
    para constituir uma Obra (ou atualizar uma existente) vs ficar como Alerta Pendente de Validação.
    Não cria obra apenas porque contém 'construção' ou 'investimento'.
    """
    texto_completo = f"{titulo or ''}. {resumo or ''}".strip()
    t_low = texto_completo.lower()

    termos_ruido = [
        "futebol", "seleção", "liga", "benfica", "sporting", "fc porto", "acidente",
        "trânsito", "cortado", "greve", "crime", "incêndio florestal", "famosos",
        "crédito à habitação", "euribor", "bolsa de valores", " Wall Street", "inflação",
        "opinião:", "podcast", "entrevista", "horóscopo"
    ]
    if any(r in t_low for r in termos_ruido):
        return {
            "relevante_radar": False,
            "evidencia_suficiente_obra": False,
            "motivo": "Tema fora do âmbito de obras e instalações técnicas."
        }

    # 1. Tem indicador concreto de ativo/obra física?
    ativos_concretos = [
        "data center", "datacenter", "centro de dados", "nova fábrica", "unidade fabril",
        "unidade industrial", "nave industrial", "parque logístico", "plataforma logística",
        "centro logístico", "entreposto logístico", "novo hospital", "ampliação do hospital",
        "centro de saúde", "unidade de saúde", "central solar", "central fotovoltaica",
        "subestação", "parque eólico", "empreitada de construção", "empreitada de reabilitação",
        "concurso público para a construção", "novo hotel", "unidade hoteleira"
    ]
    tem_ativo = any(a in t_low for a in ativos_concretos)

    # 2. Tem localização geográfica em Portugal verificável no texto?
    regiao, distrito, concelho, loc_confirmada = identificar_localizacao_portugal(texto_completo)

    # 3. Tem evidência de fase processual, concurso, adjudicação, licenciamento ou valor de obra?
    fase = identificar_fase(texto_completo)
    valor = extrair_valor_estimado(texto_completo)
    empresas, _ = extrair_entidades_verificaveis(texto_completo)
    tem_acao_concreta = (
        fase != "Por verificar"
        or valor is not None
        or len(empresas) > 0
        or fonte_tipo in ("TED Europa", "Portal BASE", "SIAIA / APA")
    )

    # Para criar/atualizar OBRA diretamente exige: Ativo Físico Concreto + Localização em PT + Evidência de Fase/Valor/Entidade
    if tem_ativo and loc_confirmada and tem_acao_concreta:
        return {
            "relevante_radar": True,
            "evidencia_suficiente_obra": True,
            "motivo": f"Evidência verificável confirmada ({concelho}, {distrito} | Fase: {fase})."
        }

    # Se tiver ativo ou termos do setor, mas faltar localização exata ou evidência de projeto, fica como Alerta Pendente
    termos_setor = ativos_concretos + [
        "empreitada", "concurso público", "adjudicação", "licenciamento", "instalações elétricas",
        "infraestrutura", "obra pública", "reabilitação", "ampliação"
    ]
    if any(k in t_low for k in termos_setor):
        motivos_falta = []
        if not tem_ativo:
            motivos_falta.append("tipo de obra/edifício específico não detalhado")
        if not loc_confirmada:
            motivos_falta.append("localização/concelho não explícito no título")
        if not tem_acao_concreta:
            motivos_falta.append("fase/entidade/concurso por confirmar")
        return {
            "relevante_radar": True,
            "evidencia_suficiente_obra": False,
            "motivo": "Requer validação humana: " + ", ".join(motivos_falta) + "."
        }

    return {
        "relevante_radar": False,
        "evidencia_suficiente_obra": False,
        "motivo": "Sem indicadores de obra ou instalação técnica."
    }


def analisar_texto_obra(texto_livre, fonte_nome="Inserção Manual", fonte_url="", data_publicacao=None):
    """
    Extrai entidades e parâmetros comerciais sustentados pelo texto da fonte.
    Nunca inventa contactos pessoais, emails, telefones, adjudicações ou empresas não citadas.
    """
    linhas_texto = [l.strip() for l in (texto_livre or "").split("\n") if l.strip()]
    primeira_frase = linhas_texto[0].split(". ")[0].strip() if linhas_texto else "Oportunidade em Análise"
    titulo = primeira_frase[:110]

    segmento = identificar_segmento(texto_livre)
    regiao, distrito, concelho, loc_confirmada = identificar_localizacao_portugal(texto_livre)
    fase = identificar_fase(texto_livre)
    valor_estimado = extrair_valor_estimado(texto_livre)
    codigo_oficial = extrair_codigo_oficial(texto_livre)

    empresas_sugeridas, papeis_identificados = extrair_entidades_verificaveis(texto_livre)
    produtos = avaliar_compatibilidade_pemsa(segmento, texto_livre)

    # Timing de fornecimento baseado na fase verificada
    if fase == "Projeto de Execução / MEP":
        timing = "Especificação técnica em aberto (Fase de Projeto / Licenciamento)"
    elif fase == "Concurso de Empreitada":
        timing = "Concurso em curso (Orçamentação por Empreiteiros / Instaladores)"
    elif fase == "Adjudicação / Pré-Construção":
        timing = "Empreitada adjudicada (Preparação de compras de materiais elétricos)"
    elif fase in ("Início de Construção", "Em Obra (Instalações a decorrer)"):
        timing = "Obra em curso (Fornecimento via instalador elétrico / distribuidor)"
    else:
        timing = "Por verificar (Fase da obra não explícita na fonte)"

    # Só menciona pessoas se o nome constar literalmente na fonte
    pessoa_match = re.search(
        r'(?:Eng\.(?:ª)?|Arqt\.(?:o|a)?)\s+([A-ZÀ-Ú][a-zA-ZÀ-ú]+(?:\s+[A-ZÀ-Ú][a-zA-ZÀ-ú]+){1,3})',
        texto_livre or ""
    )

    if empresas_sugeridas:
        partes = [f"{e['papel']}: {e['nome']} (Confirmado por fonte)" for e in empresas_sugeridas]
        responsavel_empresa = " | ".join(partes)
        estado_verificacao = "Confirmado por fonte"
    else:
        responsavel_empresa = "Por verificar (Entidades técnicas não especificadas na notícia)"
        estado_verificacao = "Por verificar"

    if pessoa_match:
        responsavel_nome = f"{pessoa_match.group(0).strip()} (Confirmado por fonte)"
    elif "Projeto" in fase:
        responsavel_nome = "Por verificar — Prioridade: Identificar Projetista MEP junto do Promotor"
    elif "Concurso" in fase:
        responsavel_nome = "Por verificar — Prioridade: Identificar Concorrentes / Empreiteiro no Caderno de Encargos"
    elif "Adjudicação" in fase or "Construção" in fase or "Obra" in fase:
        responsavel_nome = "Por verificar — Prioridade: Identificar Direção de Obra / Instalador Elétrico"
    else:
        responsavel_nome = "Por verificar"

    responsavel_cargo = "Confirmado por fonte" if empresas_sugeridas else "Por verificar"
    responsavel_contacto = "Por verificar (Não inventar email/telefone sem confirmação)"

    scoring = calcular_score_obra(
        fase=fase if fase != "Por verificar" else "Projeto de Execução / MEP",
        segmento=segmento,
        qtd_produtos_compativeis=len(produtos),
        decisores_identificados=papeis_identificados,
        tem_contactos_diretos=bool(pessoa_match),
        timing_fornecimento=timing,
        regiao=regiao if loc_confirmada else "Centro"
    )

    if not loc_confirmada:
        # Penalizar score se localização ainda estiver por verificar
        scoring["score_total"] = max(25, scoring["score_total"] - 20)
        if scoring["score_total"] < 50:
            scoring["prioridade"] = "Baixa"
        elif scoring["score_total"] < 75:
            scoring["prioridade"] = "Média"

    if "Projetista MEP" in papeis_identificados:
        proxima_acao = "Contactar o gabinete projetista confirmado pela fonte para especificar Pemsaband / Rejiband."
    elif "Empreiteiro Geral" in papeis_identificados:
        proxima_acao = "Contactar o empreiteiro confirmado pela fonte para apurar o subempreiteiro de instalações elétricas."
    elif "Promotor/Dono" in papeis_identificados:
        proxima_acao = "Contactar o promotor/entidade adjudicante para identificar o projetista MEP e calendário do concurso."
    else:
        proxima_acao = "Validar fonte oficial (Portal BASE / Município / Promotor) para identificar projetista e construtor."

    evidencia = avaliar_evidencia_item(titulo, texto_livre, fonte_tipo=fonte_nome)

    return {
        "titulo": titulo,
        "codigo_oficial": codigo_oficial,
        "segmento": segmento,
        "regiao": regiao,
        "distrito": distrito,
        "concelho": concelho,
        "localizacao_confirmada": loc_confirmada,
        "fase": fase,
        "valor_estimado": valor_estimado or "Por verificar",
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
        "estado_verificacao": estado_verificacao,
        "evidencia_suficiente_obra": evidencia["evidencia_suficiente_obra"],
        "motivo_evidencia": evidencia["motivo"],
        "resumo": (texto_livre or "")[:450] + ("..." if len(texto_livre or "") > 450 else ""),
        "fonte_nome": fonte_nome,
        "fonte_url": fonte_url,
        "data_publicacao": normalizar_data_publicacao(data_publicacao),
        "data_consulta": datetime.now().isoformat(timespec="seconds")
    }


# =====================================================================
# CONECTORES REAIS E VERIFICÁVEIS DE FONTES PÚBLICAS
# =====================================================================

FONTES_CONFIGURADAS = [
    {
        "id": "gnews_empreitadas_concursos",
        "nome": "Google News PT — Empreitadas, Concursos e Adjudicações",
        "tipo": "Imprensa / Contratação Pública",
        "metodo": "rss",
        "url": "https://news.google.com/rss/search?q=" + urllib.parse.quote(
            '("empreitada" OR "concurso público" OR "adjudicação") AND ("construção" OR "hospital" OR "fábrica" OR "escola" OR "subestação") Portugal when:30d'
        ) + "&hl=pt-PT&gl=PT&ceid=PT:pt"
    },
    {
        "id": "gnews_datacenters_industria",
        "nome": "Google News PT — Data Centers, Indústria e Logística",
        "tipo": "Imprensa Económica & Setorial",
        "metodo": "rss",
        "url": "https://news.google.com/rss/search?q=" + urllib.parse.quote(
            '("data center" OR "centro de dados" OR "nova fábrica" OR "unidade industrial" OR "plataforma logística" OR "parque logístico") Portugal when:30d'
        ) + "&hl=pt-PT&gl=PT&ceid=PT:pt"
    },
    {
        "id": "gnews_energia_saude_turismo",
        "nome": "Google News PT — Energia, Subestações, Saúde e Hotelaria",
        "tipo": "Imprensa Económica & Setorial",
        "metodo": "rss",
        "url": "https://news.google.com/rss/search?q=" + urllib.parse.quote(
            '("central solar" OR "central fotovoltaica" OR "subestação" OR "novo hospital" OR "novo hotel" OR "ampliação hospitalar") Portugal when:30d'
        ) + "&hl=pt-PT&gl=PT&ceid=PT:pt"
    },
    {
        "id": "gnews_base_ted_siaia",
        "nome": "Pesquisa Pública — Anúncios Diário da República / BASE / AIA",
        "tipo": "Portais Oficiais & Anúncios",
        "metodo": "rss",
        "url": "https://news.google.com/rss/search?q=" + urllib.parse.quote(
            '("Diário da República" OR "Portal BASE" OR "impacte ambiental" OR "consulta pública") AND ("empreitada" OR "construção" OR "central solar" OR "fábrica" OR "hospital") Portugal when:30d'
        ) + "&hl=pt-PT&gl=PT&ceid=PT:pt"
    }
]


def consultar_fonte_rss(fonte_cfg, timeout=8, session=None, max_itens=15):
    """
    Consulta um feed RSS público real com validação rigorosa de:
    - HTTP status code
    - Timeouts e erros de rede
    - Conteúdo vazio e erros de parsing XML
    - Extração da data real de publicação (<pubDate>) separada da data/hora de consulta
    """
    inicio = time.time()
    data_consulta = datetime.now().isoformat(timespec="seconds")
    resultado = {
        "fonte_id": fonte_cfg["id"],
        "fonte_nome": fonte_cfg["nome"],
        "fonte_tipo": fonte_cfg["tipo"],
        "url_consultado": fonte_cfg["url"],
        "data_consulta": data_consulta,
        "sucesso": False,
        "http_status": None,
        "erro": None,
        "itens": [],
        "tempo_ms": 0
    }

    req_getter = session.get if session is not None else requests.get
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RadarPEMSA/2.0",
        "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8"
    }

    try:
        try:
            resp = req_getter(fonte_cfg["url"], timeout=timeout, headers=headers)
        except requests.exceptions.SSLError:
            # Fallback apenas se houver proxy SSL corporativo local na máquina Windows
            resp = req_getter(fonte_cfg["url"], timeout=timeout, verify=False, headers=headers)

        resultado["http_status"] = resp.status_code

        if resp.status_code != 200:
            resultado["erro"] = f"Erro HTTP {resp.status_code} ao consultar {fonte_cfg['nome']}. Verifique disponibilidade do serviço."
            resultado["tempo_ms"] = int((time.time() - inicio) * 1000)
            return resultado

        conteudo = resp.content
        if not conteudo or not conteudo.strip():
            resultado["erro"] = f"Resposta vazia recebida de {fonte_cfg['nome']}."
            resultado["tempo_ms"] = int((time.time() - inicio) * 1000)
            return resultado

        try:
            root = ET.fromstring(conteudo)
        except ET.ParseError as e_xml:
            resultado["erro"] = f"Erro de parsing XML em {fonte_cfg['nome']}: {str(e_xml)}"
            resultado["tempo_ms"] = int((time.time() - inicio) * 1000)
            return resultado

        items_xml = root.findall(".//item")
        if not items_xml:
            # Também suporta formato Atom <entry>
            items_xml = root.findall(".//{http://www.w3.org/2005/Atom}entry")

        itens_validos = []
        for item in items_xml[:max_itens]:
            title_el = item.find("title")
            link_el = item.find("link")
            pub_el = item.find("pubDate")
            source_el = item.find("source")
            desc_el = item.find("description")

            raw_title = (title_el.text or "").strip() if title_el is not None else ""
            raw_link = (link_el.text or "").strip() if link_el is not None else ""
            raw_pub = (pub_el.text or "").strip() if pub_el is not None else None
            fonte_especifica = (
                source_el.text.strip()
                if source_el is not None and source_el.text
                else fonte_cfg["nome"]
            )

            if not raw_title or not raw_link:
                continue

            # Separar sufixo do órgão de comunicação social quando aplicável
            titulo_limpo = raw_title.rsplit(" - ", 1)[0].strip() if " - " in raw_title else raw_title

            # Limpar tags HTML simples da descrição se existir
            resumo_limpo = ""
            if desc_el is not None and desc_el.text:
                resumo_limpo = re.sub(r'<[^>]+>', ' ', desc_el.text)
                resumo_limpo = re.sub(r'\s+', ' ', resumo_limpo).strip()

            data_pub_real = normalizar_data_publicacao(raw_pub)

            itens_validos.append({
                "titulo_original": raw_title,
                "titulo": titulo_limpo,
                "link": raw_link,
                "fonte_tipo": fonte_cfg["tipo"],
                "fonte_nome": f"{fonte_especifica}",
                "fonte_conector_id": fonte_cfg["id"],
                "data_publicacao": data_pub_real,  # Data real da publicação (ou None se ausente)
                "data_consulta": data_consulta,    # Data/hora exata da consulta
                "resumo_bruto": resumo_limpo if resumo_limpo and resumo_limpo != raw_title else raw_title
            })

        resultado["sucesso"] = True
        resultado["itens"] = itens_validos
        resultado["tempo_ms"] = int((time.time() - inicio) * 1000)
        return resultado

    except requests.exceptions.Timeout:
        resultado["erro"] = f"Timeout ({timeout}s excedidos) ao contactar {fonte_cfg['nome']}. Tente aumentar o tempo limite ou verificar a ligação."
    except requests.exceptions.ConnectionError as e_conn:
        resultado["erro"] = f"Falha de ligação de rede ao contactar {fonte_cfg['nome']}: verifique o acesso à Internet ou firewall ({str(e_conn)[:120]})."
    except Exception as e_gen:
        resultado["erro"] = f"Erro inesperado em {fonte_cfg['nome']}: {type(e_gen).__name__}: {str(e_gen)[:140]}"

    resultado["tempo_ms"] = int((time.time() - inicio) * 1000)
    return resultado


def recolher_todas_as_fontes(fontes=None, timeout=8, session=None):
    """
    Executa todos os conectores configurados de forma isolada (uma falha numa fonte
    nunca impede a consulta às restantes) e devolve o relatório estruturado completo.
    """
    lista_fontes = fontes if fontes is not None else FONTES_CONFIGURADAS
    relatorios_fontes = []
    todos_itens = []

    for f_cfg in lista_fontes:
        res_f = consultar_fonte_rss(f_cfg, timeout=timeout, session=session)
        relatorios_fontes.append(res_f)
        if res_f["sucesso"]:
            todos_itens.extend(res_f["itens"])

    fontes_sucesso = sum(1 for r in relatorios_fontes if r["sucesso"])
    fontes_erro = sum(1 for r in relatorios_fontes if not r["sucesso"])

    if fontes_sucesso == len(relatorios_fontes) and len(relatorios_fontes) > 0:
        estado_global = "Sucesso"
    elif fontes_sucesso > 0:
        estado_global = "Sucesso parcial"
    else:
        estado_global = "Falha"

    return {
        "estado_global": estado_global,
        "fontes_consultadas": len(relatorios_fontes),
        "fontes_sucesso": fontes_sucesso,
        "fontes_erro": fontes_erro,
        "relatorios_fontes": relatorios_fontes,
        "itens_recolhidos": todos_itens
    }


def recolher_noticias_reais_rss(max_itens=15, timeout=8, session=None):
    """
    Função de recolha de notícias RSS com relatório explícito de erros.
    Retorna um dicionário com {'itens': [...], 'erros': [...], 'estado_global': ...}.
    """
    res = recolher_todas_as_fontes(timeout=timeout, session=session)
    erros = [r["erro"] for r in res["relatorios_fontes"] if not r["sucesso"] and r.get("erro")]
    return {
        "estado_global": res["estado_global"],
        "fontes_consultadas": res["fontes_consultadas"],
        "fontes_sucesso": res["fontes_sucesso"],
        "fontes_erro": res["fontes_erro"],
        "erros": erros,
        "relatorios_fontes": res["relatorios_fontes"],
        "itens": res["itens_recolhidos"][:max_itens]
    }
