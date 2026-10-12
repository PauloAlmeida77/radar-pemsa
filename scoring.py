"""
scoring.py - Motor de pontuação comercial PÉMSA (0 a 100 pontos).
Implementa o algoritmo de qualificação comercial com detalhe explicativo.
"""

import json

def calcular_score_obra(
    fase: str,
    segmento: str,
    qtd_produtos_compativeis: int,
    decisores_identificados: list, # lista de papeis ex: ['Projetista MEP', 'Instalador Elétrico']
    tem_contactos_diretos: bool,
    timing_fornecimento: str,
    regiao: str
) -> dict:
    """
    Calcula a pontuação de 0 a 100 e devolve o score, a classificação e o relatório detalhado.
    """
    pts_fase = 0
    expl_fase = ""

    # 1. Fase da obra (máx 30)
    fase_clean = fase.lower()
    if any(k in fase_clean for k in ["projeto de execução", "licenciamento", "estudo prévio", "especificação"]):
        pts_fase = 30
        expl_fase = "Excelente timing: Projeto em especificação técnica. Oportunidade máxima de prescrever PÉMSA."
    elif any(k in fase_clean for k in ["concurso", "adjudicação recente", "consulta ao mercado"]):
        pts_fase = 25
        expl_fase = "Muito favorável: Concurso a decorrer ou adjudicação recente de empreiteiro."
    elif any(k in fase_clean for k in ["início de construção", "estrutura", "estaleiro"]):
        pts_fase = 20
        expl_fase = "Favorável: Obra no início da estrutura civil, compras MEP a preparar."
    elif any(k in fase_clean for k in ["em obra", "instalações"]):
        pts_fase = 10
        expl_fase = "Atenção: Obra já em curso. É urgente verificar se o lote elétrico já comprou."
    else: # Acabamentos ou adiantada
        pts_fase = 4
        expl_fase = "Tardia: Obra em fase final. Apenas possíveis ampliações ou fases adicionais."

    # 2. Compatibilidade com produtos PÉMSA (máx 25)
    pts_produtos = 0
    expl_produtos = ""
    seg_clean = segmento.lower()
    if any(k in seg_clean for k in ["data center", "hospital", "industrial", "fábrica", "logística", "energia"]):
        if qtd_produtos_compativeis >= 3:
            pts_produtos = 25
            expl_produtos = f"Segmento de elevadíssimo consumo ({segmento}) com ampla gama de caminhos de cabos e tubos aplicáveis."
        else:
            pts_produtos = 20
            expl_produtos = f"Segmento de alto potencial ({segmento}) com linhas PÉMSA identificadas."
    elif any(k in seg_clean for k in ["hotel", "turismo", "comercial", "infraestruturas"]):
        pts_produtos = 18
        expl_produtos = f"Bom potencial técnico em infraestruturas terciárias ({segmento})."
    else:
        pts_produtos = 10
        expl_produtos = "Potencial moderado para instalações elétricas convencionais."

    # 3. Acesso aos decisores (máx 20)
    pts_decisores = 0
    expl_decisores = ""
    papeis_lower = [p.lower() for p in decisores_identificados]
    tem_projetista = any("projetista" in p or "engenharia" in p or "mep" in p for p in papeis_lower)
    tem_instalador = any("instalador" in p or "eletricista" in p for p in papeis_lower)
    tem_empreiteiro = any("empreiteiro" in p or "construtor" in p for p in papeis_lower)
    tem_promotor = any("promotor" in p or "dono" in p for p in papeis_lower)

    if (tem_projetista and tem_instalador) or (tem_instalador and tem_empreiteiro and tem_contactos_diretos):
        pts_decisores = 20
        expl_decisores = "Cadeia de decisão crítica identificada (Projetista MEP e Instalador/Empreiteiro)."
    elif tem_projetista or tem_instalador:
        pts_decisores = 14 if tem_contactos_diretos else 11
        expl_decisores = "Decisor chave identificado (Projetista ou Instalador elétrico)."
    elif tem_empreiteiro or tem_promotor:
        pts_decisores = 8 if tem_contactos_diretos else 5
        expl_decisores = "Apenas dono de obra ou construtor geral conhecido; falta identificar o instalador elétrico."
    else:
        pts_decisores = 0
        expl_decisores = "Nenhum decisor nem contacto identificado até ao momento."

    # 4. Possibilidade de fornecimento / Timing de compra (máx 15)
    pts_timing = 0
    expl_timing = ""
    timing_clean = (timing_fornecimento or "").lower()
    if any(k in timing_clean for k in ["especificação aberta", "não adjudicado", "sem compra fechada", "aberto"]):
        pts_timing = 15
        expl_timing = "Fornecimento em aberto: Sem evidência de marca adjudicada ou compra fechada."
    elif any(k in timing_clean for k in ["concurso aberto", "em consulta", "em orçamentação"]):
        pts_timing = 12
        expl_timing = "Momento ideal para cotação e proposta através de distribuidores parceiros."
    elif any(k in timing_clean for k in ["empreiteiro adjudicado", "instalador a negociar"]):
        pts_timing = 8
        expl_timing = "Instalador em fase de contratação/negociação de subempreitadas."
    else:
        pts_timing = 3
        expl_timing = "Risco de decisão iminente ou materiais em compra adiantada."

    # 5. Adequação geográfica (máx 10)
    pts_geo = 0
    expl_geo = ""
    regiao_clean = regiao.lower()
    if any(k in regiao_clean for k in ["norte", "porto", "braga", "aveiro", "guimarães", "lisboa", "setúbal"]):
        pts_geo = 10
        expl_geo = f"Região prioritária ({regiao}) com facilidade de apoio técnico e distribuição direta."
    elif any(k in regiao_clean for k in ["centro", "alentejo", "algarve"]):
        pts_geo = 8
        expl_geo = f"Região ativa ({regiao}) com cobertura comercial regular."
    else: # Ilhas ou interior
        pts_geo = 6
        expl_geo = f"Região {regiao} (requer coordenação logística e distribuidores locais)."

    total_score = pts_fase + pts_produtos + pts_decisores + pts_timing + pts_geo
    total_score = max(0, min(100, total_score))

    # Classificação
    if total_score >= 75:
        prioridade = "Alta"
        orientacao = "🔥 Oportunidade Prioritária — Agir já! Contactar projetista/instalador e prescrever soluções PÉMSA."
    elif total_score >= 50:
        prioridade = "Média"
        orientacao = "👀 Acompanhar — Qualificar os decisores em falta e monitorizar a evolução da fase da obra."
    else:
        prioridade = "Baixa"
        orientacao = "🔍 Investigar — Obter mais dados antes de investir tempo comercial ativo."

    breakdown = {
        "score_total": total_score,
        "prioridade": prioridade,
        "orientacao": orientacao,
        "detalhes": [
            {"criterio": "Fase da Obra", "pontos": pts_fase, "max": 30, "justificacao": expl_fase},
            {"criterio": "Compatibilidade PÉMSA", "pontos": pts_produtos, "max": 25, "justificacao": expl_produtos},
            {"criterio": "Acesso a Decisores", "pontos": pts_decisores, "max": 20, "justificacao": expl_decisores},
            {"criterio": "Timing de Fornecimento", "pontos": pts_timing, "max": 15, "justificacao": expl_timing},
            {"criterio": "Adequação Geográfica", "pontos": pts_geo, "max": 10, "justificacao": expl_geo}
        ]
    }

    return breakdown
