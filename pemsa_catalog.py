"""
pemsa_catalog.py - Catálogo e matriz técnica de produtos PÉMSA.
Mapeia os indícios de projeto, tipos de obra e produtos PÉMSA recomendados.
"""

CATALOGO_PEMSA = {
    "Caminhos de cabos em chapa (Pemsaband)": {
        "descricao": "Caminhos de cabos metálicos perfurados ou cegos com alta capacidade de carga e proteção CEM.",
        "indicadores_chave": [
            "edifícios técnicos", "hospitais", "indústria pesada", "data centers",
            "blindagem eletromagnética", "grandes vãos", "cargas elevadas", "subestações", "parques fotovoltaicos"
        ],
        "aplicacao_ideal": "Projetos terciários de grande escala, hospitais, centros comerciais e indústrias onde a proteção mecânica contínua ou imunidade a interferências é crítica.",
        "vantagem_competitiva": "Montagem rápida com sistema click, excelente comportamento ao fogo e acabamentos em galvanizado a quente (GC) e inox para ambientes agressivos."
    },
    "Caminhos de cabos em varão (Rejiband / Rejiband Rapide)": {
        "descricao": "Caminhos de cabos em grelha de varão de aço soldado. Solução líder da PÉMSA com encaixe rápido.",
        "indicadores_chave": [
            "data center", "centro de dados", "telecomunicações", "indústria alimentar",
            "farmacêutica", "logística", "armazém", "climatização", "passagens de cabos de dados", "instalações técnicas"
        ],
        "aplicacao_ideal": "Centros de dados, armazéns logísticos e indústria limpa onde a ventilação dos cabos, higiene e velocidade de instalação são determinantes.",
        "vantagem_competitiva": "Rejiband Rapide patenteado - montagem sem parafusos em 2 segundos; acabamento Black C8 para data centers e alta resistência à corrosão."
    },
    "Caminhos de cabos em PVC / Isolantes": {
        "descricao": "Calhas e caminhos de cabos em termoplástico isolante e resistente a químicos.",
        "indicadores_chave": [
            "estações de tratamento (ETAR)", "ambientes marítimos", "zonas costeiras",
            "indústria química", "adubos", "galvanoplastia", "ambientes corrosivos", "isolamento elétrico reforçado"
        ],
        "aplicacao_ideal": "Instalações próximas do mar (orla costeira de Portugal), centrais de tratamento de águas, instalações químicas e portuárias.",
        "vantagem_competitiva": "Imunidade total à corrosão e ausência de necessidade de ligação à terra em situações específicas."
    },
    "Tubos metálicos e plásticos de proteção": {
        "descricao": "Sistemas de tubagem rígida e flexível para condução e proteção mecânica e estanque de condutores.",
        "indicadores_chave": [
            "distribuição elétrica", "alimentação de máquinas", "zonas ATEX",
            "alimentação de motores", "fábricas", "instalações industriais", "parques de estacionamento", "túneis"
        ],
        "aplicacao_ideal": "Ligação a quadros elétricos, descidas de máquinas em fábricas, cablagens em ambientes severos.",
        "vantagem_competitiva": "Gama completa com conexões estanques, tubos em aço inoxidável e opções sem halogéneos."
    },
    "Bucins e entradas de cabos": {
        "descricao": "Bucins metálicos e plásticos com proteção IP68 para vedação e fixação de cabos em quadros e caixas.",
        "indicadores_chave": [
            "quadros elétricos", "caixas de junção", "máquinas industriais", "motores",
            "inversores solares", "subestações", "bombas", "estanqueidade IP68"
        ],
        "aplicacao_ideal": "Entrada em quadros gerais de baixa tensão (QGBT), caixas de derivação e inversores de parques solares.",
        "vantagem_competitiva": "Elevada gama de roscas (Métrica e PG), bucins com alívio de tração e soluções para cabos armados."
    },
    "Sistemas de suporte e fixação": {
        "descricao": "Consolas, perfis, pendurais, braçadeiras e suportes para fixação em teto, parede e chão.",
        "indicadores_chave": [
            "tetos falsos", "passerelles técnicas", "túneis de cabos", "suportes estruturais",
            "instalações suspensas", "fixação sísmica"
        ],
        "aplicacao_ideal": "Estrutura de suporte em qualquer instalação de caminhos de cabos elétricos ou telecomunicações.",
        "vantagem_competitiva": "Sistemas modulados universais, cálculo de carga certificado e acabamentos resistentes."
    }
}

def avaliar_compatibilidade_pemsa(segmento, texto_projeto=""):
    """
    Avalia quais os produtos PÉMSA mais prováveis para um determinado tipo de obra e texto descritivo.
    Retorna uma lista de recomendações com nível de potencial.
    """
    texto_lower = (texto_projeto + " " + segmento).lower()
    recomendacoes = []

    # Regras por segmento e keywords
    for familia, info in CATALOGO_PEMSA.items():
        score_hits = 0
        evidencias = []
        for keyword in info["indicadores_chave"]:
            if keyword in texto_lower:
                score_hits += 1
                evidencias.append(keyword)

        # Regras diretas por segmento
        if "data center" in segmento.lower() and "varão" in familia:
            score_hits += 3
        if "hospital" in segmento.lower() and "chapa" in familia:
            score_hits += 3
        if "logística" in segmento.lower() and "varão" in familia:
            score_hits += 2
        if "industrial" in segmento.lower() and ("tubos" in familia or "chapa" in familia or "bucins" in familia):
            score_hits += 2

        if score_hits >= 2:
            nivel = "Compatibilidade Confirmada" if score_hits >= 3 else "Potencial Teórico"
            recomendacoes.append({
                "familia_produto": familia,
                "nivel_potencial": nivel,
                "especificacao_detalhe": f"Indícios detetados: {', '.join(evidencias[:3]) if evidencias else 'Padrão do segmento'}",
                "vantagem": info["vantagem_competitiva"]
            })
        elif score_hits == 1 or "suporte" in familia:
            # Suportes acompanham sempre
            recomendacoes.append({
                "familia_produto": familia,
                "nivel_potencial": "Potencial Teórico",
                "especificacao_detalhe": f"Recomendado como sistema complementar ({info['descricao'][:50]}...)",
                "vantagem": info["vantagem_competitiva"]
            })

    return recomendacoes
