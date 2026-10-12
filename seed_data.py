"""
seed_data.py - Popula a base de dados com projetos, empresas, contactos e tarefas realistas em Portugal.
"""

import json
from datetime import date, timedelta
from database import get_connection, init_db, inserir_obra
from scoring import calcular_score_obra

def popular_dados_iniciais():
    """Insere dados de demonstração detalhados na base de dados SQLite."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    # Verificar se já existem dados
    cursor.execute("SELECT COUNT(*) FROM obras")
    if cursor.fetchone()[0] > 0:
        # Atualizar dados dos responsáveis nas obras existentes
        updates = [
            ("PEMSA-2026-SINES", "Eng. Tiago Mendonça", "Diretor de Projetos MEP / Eletrotécnica", "Quadrante Engenharia & MEP", "+351 919 123 456 | tiago.mendonca@quadrante-group.com"),
            ("PEMSA-2026-HLISBOA", "Eng. Marco Silva", "Diretor de Produção e MEP", "Casais Engenharia / Consórcio Hospitalar", "+351 917 889 900 | marco.silva@casais.pt"),
            ("PEMSA-2026-FAMALICAO", "Rui Peixoto", "Gestor de Obra - Instalações Industriais", "CME - Construção e Manutenção Eletromecânica", "+351 925 112 233 | rui.peixoto@cme.pt"),
            ("PEMSA-2026-CASTANHEIRA", "Eng.ª Sofia Henriques", "Projetista Eletrotécnica Sénior", "Afaconsult Engenharia e Projetos", "+351 934 567 890 | sofia.henriques@afaconsult.com"),
            ("PEMSA-2026-COMPORTA", "Eng. Marco Silva", "Diretor Técnico de Obra MEP", "Casais Engenharia e Construção", "+351 917 889 900 | marco.silva@casais.pt"),
            ("PEMSA-2026-MADEIRA", "Eng. Duarte Freitas", "Responsável Técnico MEP", "Mota-Engil Engenharia", "+351 220 411 000 | suprimentos@mota-engil.pt"),
            ("PEMSA-2026-MAIA", "Eng. António Barbosa", "Diretor de Engenharia Elétrica", "Projenel Projetos e Consultoria Elétrica", "+351 253 200 400 | geral@projenel.pt"),
        ]
        for ref, n, c, e, cont in updates:
            cursor.execute("""
                UPDATE obras SET responsavel_nome = ?, responsavel_cargo = ?, responsavel_empresa = ?, responsavel_contacto = ?
                WHERE codigo_ref = ?
            """, (n, c, e, cont, ref))
        conn.commit()
        conn.close()
        return

    print("A popular dados de demonstração para o Radar PÉMSA...")

    # 1. Inserir Empresas do Ecossistema Português
    empresas = [
        # Promotores
        {"nome": "Start Campus S.A.", "nif": "516123456", "tipo": "Promotor", "distrito": "Setúbal", "cidade": "Sines", "telefone": "+351 269 000 100", "email": "projects@startcampus.pt", "website": "https://startcampus.pt", "nivel_relacionamento": "Contacto Frio", "notas": "Promotor do campus de data centers Sines 4.0."},
        {"nome": "Panattoni Portugal Investimentos", "nif": "515987654", "tipo": "Promotor", "distrito": "Lisboa", "cidade": "Lisboa", "telefone": "+351 210 456 789", "email": "info-pt@panattoni.com", "website": "https://panattoni.com", "nivel_relacionamento": "Contacto Frio", "notas": "Maior promotor logístico privado da Europa, expansão forte no Ribatejo e Norte."},
        {"nome": "Unidade Local de Saúde de Lisboa Oriental", "nif": "509876543", "tipo": "Promotor", "distrito": "Lisboa", "cidade": "Lisboa", "telefone": "+351 218 000 000", "email": "geral@chlc.min-saude.pt", "website": "https://min-saude.pt", "nivel_relacionamento": "Sem Contacto", "notas": "Entidade pública promotora do novo Hospital de Todos os Santos."},
        {"nome": "Vanguard Properties Portugal", "nif": "514332211", "tipo": "Promotor", "distrito": "Setúbal", "cidade": "Grândola", "telefone": "+351 213 100 200", "email": "investments@vanguard-properties.com", "website": "https://vanguard-properties.com", "nivel_relacionamento": "Sem Contacto", "notas": "Promotor imobiliário de luxo, projetos turísticos na Comporta e Lisboa."},
        {"nome": "Continental Mabor S.A.", "nif": "500123456", "tipo": "Promotor", "distrito": "Braga", "cidade": "Vila Nova de Famalicão", "telefone": "+351 252 000 500", "email": "info.mabor@continental.com", "website": "https://continental.pt", "nivel_relacionamento": "Cliente Ativo", "notas": "Forte investimento contínuo em ampliação de linhas fabris automotivas."},

        # Projetistas / Gabinetes de Engenharia MEP
        {"nome": "Quadrante Engenharia & MEP", "nif": "504556677", "tipo": "Projetista MEP", "distrito": "Lisboa", "cidade": "Lisboa", "telefone": "+351 217 815 000", "email": "mep@quadrante-group.com", "website": "https://quadrante-group.com", "nivel_relacionamento": "Parceiro Habitual", "notas": "Gabinete de engenharia de referência para infraestruturas críticas e hospitais. Especificam habitualmente caminhos de cabos em chapa e varão."},
        {"nome": "Afaconsult Engenharia e Projetos", "nif": "502889900", "tipo": "Projetista MEP", "distrito": "Porto", "cidade": "Porto", "telefone": "+351 226 089 500", "email": "porto@afaconsult.com", "website": "https://afaconsult.com", "nivel_relacionamento": "Parceiro Habitual", "notas": "Projetistas líderes em edifícios de grande porte e estruturas industriais no Norte."},
        {"nome": "Projenel Projetos e Consultoria Elétrica", "nif": "507665544", "tipo": "Projetista MEP", "distrito": "Braga", "cidade": "Braga", "telefone": "+351 253 200 400", "email": "geral@projenel.pt", "website": "https://projenel.pt", "nivel_relacionamento": "Contacto Frio", "notas": "Especialistas em projetos elétricos industriais e subestações."},

        # Empreiteiros Gerais
        {"nome": "Casais Engenharia e Construção", "nif": "500223344", "tipo": "Empreiteiro Geral", "distrito": "Braga", "cidade": "Braga", "telefone": "+351 253 305 400", "email": "compras@casais.pt", "website": "https://casais.pt", "nivel_relacionamento": "Parceiro Habitual", "notas": "Grupo construtor de topo ibérico com fortes obras industriais e hoteleiras."},
        {"nome": "Mota-Engil Engenharia", "nif": "500258741", "tipo": "Empreiteiro Geral", "distrito": "Porto", "cidade": "Porto", "telefone": "+351 220 411 000", "email": "suprimentos@mota-engil.pt", "website": "https://mota-engil.pt", "nivel_relacionamento": "Parceiro Habitual", "notas": "Líder de contratação pública e grandes infraestruturas."},
        {"nome": "DST Group (Domingos da Silva Teixeira)", "nif": "501334455", "tipo": "Empreiteiro Geral", "distrito": "Braga", "cidade": "Braga", "telefone": "+351 253 600 700", "email": "geral@dstsgps.com", "website": "https://dstsgps.com", "nivel_relacionamento": "Parceiro Habitual", "notas": "Grupo com divisão de engenharia civil e divisão elétrica (DSTELE)."},

        # Instaladores Elétricos
        {"nome": "Sotécnica - VINCI Energies Portugal", "nif": "500334455", "tipo": "Instalador Elétrico", "distrito": "Lisboa", "cidade": "Loures", "telefone": "+351 219 494 000", "email": "compras.mep@sotecnica.pt", "website": "https://sotecnica.pt", "nivel_relacionamento": "Cliente Ativo", "notas": "Instalador MEP líder em data centers e hospitais. Comprador chave de Rejiband e Pemsaband."},
        {"nome": "CME - Construção e Manutenção Eletromecânica", "nif": "501889911", "tipo": "Instalador Elétrico", "distrito": "Porto", "cidade": "Maia", "telefone": "+351 229 438 000", "email": "eletricidade@cme.pt", "website": "https://cme.pt", "nivel_relacionamento": "Cliente Ativo", "notas": "Forte presença em redes elétricas, telecomunicações e grandes instalações fabris."},
        {"nome": "Instalectra - Instalações Elétricas Industriais", "nif": "503998877", "tipo": "Instalador Elétrico", "distrito": "Porto", "cidade": "Vila Nova de Gaia", "telefone": "+351 227 800 900", "email": "orcamentos@instalectra.pt", "website": "https://instalectra.pt", "nivel_relacionamento": "Contacto Frio", "notas": "Instalador com forte atividade em armazéns logísticos e fábricas no Grande Porto."}
    ]

    empresa_ids = {}
    for emp in empresas:
        cursor.execute("""
            INSERT INTO empresas (nome, nif, tipo, distrito, cidade, telefone, email, website, nivel_relacionamento, notas)
            VALUES (:nome, :nif, :tipo, :distrito, :cidade, :telefone, :email, :website, :nivel_relacionamento, :notas)
        """, emp)
        empresa_ids[emp["nome"]] = cursor.lastrowid

    # 2. Inserir Pessoas de Contacto
    contactos = [
        {"empresa_nome": "Quadrante Engenharia & MEP", "nome": "Eng. Tiago Mendonça", "cargo": "Diretor de Projetos MEP / Eletrotécnica", "departamento": "Engenharia Elétrica", "telefone": "+351 919 123 456", "email": "tiago.mendonca@quadrante-group.com", "linkedin": "linkedin.com/in/tiago-mendonca-mep", "notas": "Decisor chave de prescrição técnica. Muito recetivo a catálogos BIM e ensaios de fogo."},
        {"empresa_nome": "Afaconsult Engenharia e Projetos", "nome": "Eng.ª Sofia Henriques", "cargo": "Projetista Eletrotécnica Sénior", "departamento": "Instalações Especiais", "telefone": "+351 934 567 890", "email": "sofia.henriques@afaconsult.com", "linkedin": "linkedin.com/in/sofia-henriques-eng", "notas": "Responsável pelo caderno de encargos do parque logístico de Castanheira."},
        {"empresa_nome": "Sotécnica - VINCI Energies Portugal", "nome": "Carlos Fonseca", "cargo": "Diretor de Compras de Materiais Elétricos", "departamento": "Suprimentos MEP", "telefone": "+351 961 223 344", "email": "carlos.fonseca@sotecnica.pt", "linkedin": "linkedin.com/in/carlos-fonseca-procurement", "notas": "Negocia compras de caminhos de cabos para os data centers. Prefere cotação direta com distribuidores Rexel / Sonepar."},
        {"empresa_nome": "CME - Construção e Manutenção Eletromecânica", "nome": "Rui Peixoto", "cargo": "Gestor de Obra - Instalações Industriais", "departamento": "Direção de Obras Norte", "telefone": "+351 925 112 233", "email": "rui.peixoto@cme.pt", "linkedin": "linkedin.com/in/rui-peixoto-cme", "notas": "Acompanha a execução elétrica da ampliação fabril em Famalicão."},
        {"empresa_nome": "Casais Engenharia e Construção", "nome": "Eng. Marco Silva", "cargo": "Diretor de Produção e MEP", "departamento": "Edificação Especial", "telefone": "+351 917 889 900", "email": "marco.silva@casais.pt", "linkedin": "linkedin.com/in/marco-silva-casais", "notas": "Coordena as subempreitadas elétricas do consórcio hospitalar."}
    ]

    contacto_ids = {}
    for c in contactos:
        emp_id = empresa_ids.get(c["empresa_nome"])
        if emp_id:
            cursor.execute("""
                INSERT INTO contactos (empresa_id, nome, cargo, departamento, telefone, email, linkedin, notas)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (emp_id, c["nome"], c["cargo"], c["departamento"], c["telefone"], c["email"], c["linkedin"], c["notas"]))
            contacto_ids[c["nome"]] = cursor.lastrowid

    conn.commit()
    conn.close()

    # 3. Inserir Obras Detalhadas com Scoring e Relações
    obras_iniciais = [
        # OBRA 1: Mega Data Center Sines 4.0
        {
            "obra": {
                "titulo": "Campus de Data Centers Sines 4.0 — Fase 2 (Edifícios H1 e H2)",
                "codigo_ref": "PEMSA-2026-SINES",
                "segmento": "Data Center",
                "regiao": "Sul",
                "distrito": "Setúbal",
                "concelho": "Sines",
                "morada_localizacao": "ZILS - Zona Industrial e Logística de Sines",
                "lat": 37.9538,
                "lon": -8.8698,
                "fase": "Projeto de Execução / MEP",
                "status_comercial": "Em Qualificação",
                "valor_estimado": "145.000.000 €",
                "prazo_previsto": "2026 - 2028",
                "data_detecao": (date.today() - timedelta(days=4)).isoformat(),
                "fonte_tipo": "Notícia / Comunicado do Promotor",
                "fonte_nome": "Sines Green Data Hub Official & Reuters",
                "fonte_url": "https://startcampus.pt/press/fase2-sines40",
                "resumo": "Expansão de 60MW de capacidade com dois novos edifícios de servidores e salas técnicas. Forte exigência de caminhos de cabos em varão de alta ventilação, acabamento Black C8 e suportação sísmica para tetos técnicos suspensos.",
                "timing_fornecimento": "Especificação técnica em aberto (sem compra fechada)",
                "proxima_acao": "Apresentar ao projetista Quadrante e ao instalador Sotécnica as soluções Rejiband Rapide Black C8 e acessórios de montagem rápida.",
                "notas_comerciais": "Oportunidade de topo a nível ibérico. O volume previsto de caminhos de cabos ultrapassa os 40.000 metros lineares.",
                "responsavel_nome": "Eng. Tiago Mendonça",
                "responsavel_cargo": "Diretor de Projetos MEP / Eletrotécnica",
                "responsavel_empresa": "Quadrante Engenharia & MEP",
                "responsavel_contacto": "+351 919 123 456 | tiago.mendonca@quadrante-group.com"
            },
            "empresas": [
                {"empresa_id": empresa_ids["Start Campus S.A."], "papel": "Promotor/Dono", "confirmado": 1, "notas": "Dono do investimento."},
                {"empresa_id": empresa_ids["Quadrante Engenharia & MEP"], "papel": "Projetista MEP", "confirmado": 1, "notas": "A desenvolver cadernos de encargos de instalações especiais."},
                {"empresa_id": empresa_ids["Sotécnica - VINCI Energies Portugal"], "papel": "Instalador Elétrico", "confirmado": 0, "notas": "Forte candidato a adjudicatário do lote elétrico."}
            ],
            "produtos": [
                {"familia_produto": "Caminhos de cabos em varão (Rejiband / Rejiband Rapide)", "nivel_potencial": "Oportunidade Validada", "especificacao_detalhe": "Rejiband acabamento Black C8 / Eletrozincado, larguras 300mm a 600mm para salas de servidores."},
                {"familia_produto": "Caminhos de cabos em chapa (Pemsaband)", "nivel_potencial": "Compatibilidade Confirmada", "especificacao_detalhe": "Galerias técnicas principais e subestação do campus."},
                {"familia_produto": "Sistemas de suporte e fixação", "nivel_potencial": "Compatibilidade Confirmada", "especificacao_detalhe": "Perfis e pendurais reguláveis para instalação sob piso técnico e teto suspenso."},
                {"familia_produto": "Bucins e entradas de cabos", "nivel_potencial": "Potencial Teórico", "especificacao_detalhe": "Entrada em quadros elétricos de distribuição e geradores."}
            ]
        },

        # OBRA 2: Novo Hospital de Lisboa Oriental
        {
            "obra": {
                "titulo": "Novo Hospital de Lisboa Oriental (Todos os Santos) — Lote de Instalações Técnicas",
                "codigo_ref": "PEMSA-2026-HLISBOA",
                "segmento": "Hospital / Saúde",
                "regiao": "Sul",
                "distrito": "Lisboa",
                "concelho": "Lisboa",
                "morada_localizacao": "Parque de Saúde de Marvila / Chelas",
                "lat": 38.7420,
                "lon": -9.1080,
                "fase": "Concurso de Empreitada",
                "status_comercial": "Nova Oportunidade",
                "valor_estimado": "380.000.000 €",
                "prazo_previsto": "2026 - 2029",
                "data_detecao": (date.today() - timedelta(days=2)).isoformat(),
                "fonte_tipo": "Portal BASE & TED",
                "fonte_nome": "Base.gov.pt Concurso Público n.º 2026/SAUDE-01",
                "fonte_url": "https://www.base.gov.pt/Base4/pt/resultados/?type=contratos&query=hospital+lisboa+oriental",
                "resumo": "Construção do maior hospital central de Lisboa com mais de 800 camas e múltiplos blocos cirúrgicos. O projeto elétrico exige caminhos de cabos com ensaios de resistência ao fogo E90 e elevada imunidade a interferências CEM.",
                "timing_fornecimento": "Concurso aberto em consulta ao mercado",
                "proxima_acao": "Reunir com os gabinetes de orçamentação dos consórcios concorrentes (Mota-Engil e Casais) e prescrever Pemsaband GC / E90.",
                "notas_comerciais": "Projeto crítico de contratação pública. Homologações de segurança contra incêndios da PÉMSA são um fator diferenciador.",
                "responsavel_nome": "Eng. Marco Silva",
                "responsavel_cargo": "Diretor de Produção e MEP",
                "responsavel_empresa": "Casais Engenharia / Consórcio Hospitalar",
                "responsavel_contacto": "+351 917 889 900 | marco.silva@casais.pt"
            },
            "empresas": [
                {"empresa_id": empresa_ids["Unidade Local de Saúde de Lisboa Oriental"], "papel": "Promotor/Dono", "confirmado": 1, "notas": "Entidade adjudicante pública."},
                {"empresa_id": empresa_ids["Mota-Engil Engenharia"], "papel": "Empreiteiro Geral", "confirmado": 1, "notas": "Líder de consórcio construtor."},
                {"empresa_id": empresa_ids["Quadrante Engenharia & MEP"], "papel": "Projetista MEP", "confirmado": 1, "notas": "Projetistas de instalações técnicas especiais."}
            ],
            "produtos": [
                {"familia_produto": "Caminhos de cabos em chapa (Pemsaband)", "nivel_potencial": "Oportunidade Validada", "especificacao_detalhe": "Pemsaband perfurado com certificação de resistência ao fogo E90 para corredores técnicos e blocos operatórios."},
                {"familia_produto": "Tubos metálicos e plásticos de proteção", "nivel_potencial": "Compatibilidade Confirmada", "especificacao_detalhe": "Tubagem sem halogéneos (LSOH) para áreas de internamento."},
                {"familia_produto": "Sistemas de suporte e fixação", "nivel_potencial": "Compatibilidade Confirmada", "especificacao_detalhe": "Suportação de alta carga para caminhos pesados."}
            ]
        },

        # OBRA 3: Nova Unidade Fabril de Baterias em Famalicão
        {
            "obra": {
                "titulo": "Nova Unidade Industrial Fabril de Componentes Automotivos — Famalicão",
                "codigo_ref": "PEMSA-2026-FAMALICAO",
                "segmento": "Industrial / Fábricas",
                "regiao": "Norte",
                "distrito": "Braga",
                "concelho": "Vila Nova de Famalicão",
                "morada_localizacao": "Parque Industrial de Lousado",
                "lat": 41.3533,
                "lon": -8.5305,
                "fase": "Início de Construção",
                "status_comercial": "Contacto Feito",
                "valor_estimado": "42.000.000 €",
                "prazo_previsto": "2026 - 2027",
                "data_detecao": (date.today() - timedelta(days=7)).isoformat(),
                "fonte_tipo": "Notícia Económica / Licenciamento",
                "fonte_nome": "Jornal ECO & Município de Famalicão",
                "fonte_url": "https://eco.sapo.pt/2026/fabrica-famalicao",
                "resumo": "Construção de nova nave de produção automatizada de 25.000 m2. Trabalhos de fundações em curso. Instalador elétrico CME já no terreno a preparar encomendas de caminho de cabos e tubos industriais.",
                "timing_fornecimento": "Instalador adjudicado mas materiais elétricos em cotação",
                "proxima_acao": "Enviar cotação formal de Rejiband e tubos industriais ao Rui Peixoto (CME) via distribuidor do Norte.",
                "notas_comerciais": "Contacto positivo realizado no dia 10. Estão recetivos ao sistema de encaixe rápido Rejiband Rapide devido ao prazo apertado da obra.",
                "responsavel_nome": "Rui Peixoto",
                "responsavel_cargo": "Gestor de Obra - Instalações Industriais",
                "responsavel_empresa": "CME - Construção e Manutenção Eletromecânica",
                "responsavel_contacto": "+351 925 112 233 | rui.peixoto@cme.pt"
            },
            "empresas": [
                {"empresa_id": empresa_ids["Continental Mabor S.A."], "papel": "Promotor/Dono", "confirmado": 1, "notas": "Investidor direto."},
                {"empresa_id": empresa_ids["DST Group (Domingos da Silva Teixeira)"], "papel": "Empreiteiro Geral", "confirmado": 1, "notas": "Execução civil da nave."},
                {"empresa_id": empresa_ids["CME - Construção e Manutenção Eletromecânica"], "papel": "Instalador Elétrico", "confirmado": 1, "notas": "Subempreiteiro responsável por toda a eletrificação."}
            ],
            "produtos": [
                {"familia_produto": "Caminhos de cabos em varão (Rejiband / Rejiband Rapide)", "nivel_potencial": "Oportunidade Validada", "especificacao_detalhe": "Rejiband Rapide com acabamento galvanizado reforçado para linhas de montagem."},
                {"familia_produto": "Tubos metálicos e plásticos de proteção", "nivel_potencial": "Compatibilidade Confirmada", "especificacao_detalhe": "Tubo rígido de aço para descidas de máquinas e alimentação de robótica."},
                {"familia_produto": "Bucins e entradas de cabos", "nivel_potencial": "Compatibilidade Confirmada", "especificacao_detalhe": "Bucins metálicos IP68 para quadros de automação e motores."}
            ]
        },

        # OBRA 4: Panattoni Park Castanheira do Ribatejo
        {
            "obra": {
                "titulo": "Plataforma Logística Panattoni Park Castanheira — Bloco Logístico A & B",
                "codigo_ref": "PEMSA-2026-CASTANHEIRA",
                "segmento": "Logística / Armazéns",
                "regiao": "Sul",
                "distrito": "Lisboa",
                "concelho": "Vila Franca de Xira",
                "morada_localizacao": "Castanheira do Ribatejo, EN1",
                "lat": 38.9950,
                "lon": -8.9720,
                "fase": "Projeto de Execução / MEP",
                "status_comercial": "Nova Oportunidade",
                "valor_estimado": "35.000.000 €",
                "prazo_previsto": "2026 - 2027",
                "data_detecao": (date.today() - timedelta(days=1)).isoformat(),
                "fonte_tipo": "Comunicado de Imprensa do Promotor",
                "fonte_nome": "Construir.pt & Panattoni PR",
                "fonte_url": "https://construir.pt/panattoni-castanheira",
                "resumo": "Projeto logístico de última geração com 50.000 m2 cobertos, cais de carga automatizados e certificação ambiental BREEAM Excellent. Exige soluções de instalação rápida em varão sob cobertura metálica.",
                "timing_fornecimento": "Especificação técnica em aberto (sem compra fechada)",
                "proxima_acao": "Contactar a Eng.ª Sofia Henriques da Afaconsult para garantir a especificação do sistema Rejiband nas telas do projeto.",
                "notas_comerciais": "Projetistas da Afaconsult conhecem bem a PÉMSA. Promotor pan-europeu com dezenas de armazéns na Península Ibérica.",
                "responsavel_nome": "Eng.ª Sofia Henriques",
                "responsavel_cargo": "Projetista Eletrotécnica Sénior",
                "responsavel_empresa": "Afaconsult Engenharia e Projetos",
                "responsavel_contacto": "+351 934 567 890 | sofia.henriques@afaconsult.com"
            },
            "empresas": [
                {"empresa_id": empresa_ids["Panattoni Portugal Investimentos"], "papel": "Promotor/Dono", "confirmado": 1, "notas": "Promotor logístico."},
                {"empresa_id": empresa_ids["Afaconsult Engenharia e Projetos"], "papel": "Projetista MEP", "confirmado": 1, "notas": "Gabinete responsável pelo projeto de eletricidade e AVAC."}
            ],
            "produtos": [
                {"familia_produto": "Caminhos de cabos em varão (Rejiband / Rejiband Rapide)", "nivel_potencial": "Oportunidade Validada", "especificacao_detalhe": "Rejiband 400x60mm para caminhos principais sob as vigas metálicas de cobertura."},
                {"familia_produto": "Sistemas de suporte e fixação", "nivel_potencial": "Compatibilidade Confirmada", "especificacao_detalhe": "Braçadeiras de viga metálica e pendurais de varão roscado rápido."}
            ]
        },

        # OBRA 5: Eco-Resort de Luxo na Comporta
        {
            "obra": {
                "titulo": "Empreendimento Hoteleiro & Eco-Resort Muda Reserve — Comporta",
                "codigo_ref": "PEMSA-2026-COMPORTA",
                "segmento": "Hotel / Turismo",
                "regiao": "Sul",
                "distrito": "Setúbal",
                "concelho": "Grândola",
                "morada_localizacao": "Muda, Comporta",
                "lat": 38.3120,
                "lon": -8.7230,
                "fase": "Início de Construção",
                "status_comercial": "Em Qualificação",
                "valor_estimado": "55.000.000 €",
                "prazo_previsto": "2026 - 2028",
                "data_detecao": (date.today() - timedelta(days=12)).isoformat(),
                "fonte_tipo": "Licenciamento Municipal",
                "fonte_nome": "Câmara Municipal de Grândola",
                "fonte_url": "https://cm-grandola.pt/licenciamento-muda",
                "resumo": "Unidade hoteleira de 5 estrelas com 80 vilas e edifício central. Localização em zona costeira com maresia. Requer caminhos de cabos em PVC e inox resistentes ao ambiente salino e tubagem isolante embutida.",
                "timing_fornecimento": "Empreiteiro Casais adjudicado, pacote elétrico em consulta",
                "proxima_acao": "Apresentar ao Eng. Marco Silva da Casais o catálogo de caminhos em PVC e acessórios de inox para ambiente marítimo.",
                "notas_comerciais": "Excelente montra para a gama de PVC isolante e acabamento Inox 316L da PÉMSA.",
                "responsavel_nome": "Eng. Marco Silva",
                "responsavel_cargo": "Diretor Técnico de Obra MEP",
                "responsavel_empresa": "Casais Engenharia e Construção",
                "responsavel_contacto": "+351 917 889 900 | marco.silva@casais.pt"
            },
            "empresas": [
                {"empresa_id": empresa_ids["Vanguard Properties Portugal"], "papel": "Promotor/Dono", "confirmado": 1, "notas": "Promotor."},
                {"empresa_id": empresa_ids["Casais Engenharia e Construção"], "papel": "Empreiteiro Geral", "confirmado": 1, "notas": "Construção geral."}
            ],
            "produtos": [
                {"familia_produto": "Caminhos de cabos em PVC / Isolantes", "nivel_potencial": "Oportunidade Validada", "especificacao_detalhe": "Caminhos em PVC isolante para zonas exteriores e cave técnica exposta à maresia."},
                {"familia_produto": "Tubos metálicos e plásticos de proteção", "nivel_potencial": "Compatibilidade Confirmada", "especificacao_detalhe": "Tubagem de PVC reforçada para passagens enterradas e lajes."}
            ]
        },

        # OBRA 6: Reabilitação e Ampliação do Hospital Central do Funchal
        {
            "obra": {
                "titulo": "Novo Hospital Central da Madeira — Funchal (Instalações Técnicas)",
                "codigo_ref": "PEMSA-2026-MADEIRA",
                "segmento": "Hospital / Saúde",
                "regiao": "Madeira",
                "distrito": "Madeira",
                "concelho": "Funchal",
                "morada_localizacao": "Santa Rita, Funchal",
                "lat": 32.6511,
                "lon": -16.9355,
                "fase": "Em Obra (Instalações a decorrer)",
                "status_comercial": "Contacto Feito",
                "valor_estimado": "205.000.000 €",
                "prazo_previsto": "2026 - 2028",
                "data_detecao": (date.today() - timedelta(days=20)).isoformat(),
                "fonte_tipo": "Portal BASE",
                "fonte_nome": "Jornal Oficial da Região Autónoma da Madeira",
                "fonte_url": "https://joram.madeira.gov.pt/hospital-central",
                "resumo": "Execução da estrutura e início das subempreitadas de canalizações e eletricidade. Obras de grande envergadura com necessidade de fornecimento contínuo de caminhos de cabos e apoio logístico insular.",
                "timing_fornecimento": "Instaladores no terreno mas novos lotes de ampliação em cotação",
                "proxima_acao": "Articular com o distribuidor parceiro no Funchal para reforçar stock de varão Rejiband e curvas rápidas.",
                "notas_comerciais": "Logística marítima requer planeamento de 2 semanas de antecedência.",
                "responsavel_nome": "Eng. Duarte Freitas",
                "responsavel_cargo": "Responsável Técnico MEP",
                "responsavel_empresa": "Mota-Engil Engenharia",
                "responsavel_contacto": "+351 220 411 000 | suprimentos@mota-engil.pt"
            },
            "empresas": [
                {"empresa_id": empresa_ids["Mota-Engil Engenharia"], "papel": "Empreiteiro Geral", "confirmado": 1, "notas": "Consórcio construtor insular."}
            ],
            "produtos": [
                {"familia_produto": "Caminhos de cabos em chapa (Pemsaband)", "nivel_potencial": "Compatibilidade Confirmada", "especificacao_detalhe": "Distribuição em caminhos principais de infraestrutura hospitalar."},
                {"familia_produto": "Caminhos de cabos em varão (Rejiband / Rejiband Rapide)", "nivel_potencial": "Compatibilidade Confirmada", "especificacao_detalhe": "Redes de dados e cablagem de telecomunicações estruturada."}
            ]
        },

        # OBRA 7: Centro Logístico Frigorífico Maia Norte
        {
            "obra": {
                "titulo": "Novo Centro de Distribuição e Frio Industrial — Maia Norte",
                "codigo_ref": "PEMSA-2026-MAIA",
                "segmento": "Logística / Armazéns",
                "regiao": "Norte",
                "distrito": "Porto",
                "concelho": "Maia",
                "morada_localizacao": "Zona Industrial da Maia I",
                "lat": 41.2355,
                "lon": -8.6210,
                "fase": "Projeto de Execução / MEP",
                "status_comercial": "Nova Oportunidade",
                "valor_estimado": "18.500.000 €",
                "prazo_previsto": "2026 - 2027",
                "data_detecao": (date.today() - timedelta(days=3)).isoformat(),
                "fonte_tipo": "Notícia / Revista da Construção",
                "fonte_nome": "Construção Magazine",
                "fonte_url": "https://construcaomagazine.pt/maia-frio-logistica",
                "resumo": "Armazém logístico com câmaras de frio e controlo de humidade para o setor agroalimentar. Exige caminhos de cabos em varão eletrozincado de fácil limpeza e acabamento anticorrosivo para evitar condensação.",
                "timing_fornecimento": "Especificação técnica em aberto (sem compra fechada)",
                "proxima_acao": "Contactar gabinete de engenharia Projenel em Braga e apresentar soluções Rejiband com garantia de resistência higiénica alimentar.",
                "notas_comerciais": "Excelente localização no Porto/Norte com contacto rápido.",
                "responsavel_nome": "Eng. António Barbosa",
                "responsavel_cargo": "Diretor de Engenharia Elétrica",
                "responsavel_empresa": "Projenel Projetos e Consultoria Elétrica",
                "responsavel_contacto": "+351 253 200 400 | geral@projenel.pt"
            },
            "empresas": [
                {"empresa_id": empresa_ids["Projenel Projetos e Consultoria Elétrica"], "papel": "Projetista MEP", "confirmado": 1, "notas": "Projetistas das instalações eletrotécnicas."}
            ],
            "produtos": [
                {"familia_produto": "Caminhos de cabos em varão (Rejiband / Rejiband Rapide)", "nivel_potencial": "Oportunidade Validada", "especificacao_detalhe": "Varão para armazém e câmaras frias, excelente ventilação e facilidade de higienização."},
                {"familia_produto": "Tubos metálicos e plásticos de proteção", "nivel_potencial": "Potencial Teórico", "especificacao_detalhe": "Tubo rígido estanque para cais de carga."}
            ]
        }
    ]

    for item in obras_iniciais:
        dados_obra = item["obra"]
        empresas_interv = item["empresas"]
        produtos_pemsa = item["produtos"]

        # Calcular score real via scoring engine
        papeis = [e.get("papel", "") for e in empresas_interv]
        tem_contactos = any(e.get("papel") in ["Projetista MEP", "Instalador Elétrico"] for e in empresas_interv)

        scoring_res = calcular_score_obra(
            fase=dados_obra["fase"],
            segmento=dados_obra["segmento"],
            qtd_produtos_compativeis=len(produtos_pemsa),
            decisores_identificados=papeis,
            tem_contactos_diretos=tem_contactos,
            timing_fornecimento=dados_obra["timing_fornecimento"],
            regiao=dados_obra["regiao"]
        )

        dados_obra["score"] = scoring_res["score_total"]
        dados_obra["prioridade"] = scoring_res["prioridade"]
        dados_obra["score_breakdown"] = json.dumps(scoring_res, ensure_ascii=False)

        obra_id = inserir_obra(dados_obra, empresas_interv, produtos_pemsa)

    # 4. Inserir Tarefas Comerciais de Seguimento (CRM)
    tarefas_iniciais = [
        {
            "obra_id": 1, # Data Center Sines
            "empresa_id": empresa_ids["Quadrante Engenharia & MEP"],
            "contacto_id": contacto_ids.get("Eng. Tiago Mendonça"),
            "titulo": "Apresentar Rejiband Rapide Black C8 ao Eng. Tiago Mendonça (Data Center Sines)",
            "tipo": "Apresentação Técnica",
            "data_limite": (date.today() - timedelta(days=1)).isoformat(), # em atraso para alertar
            "prioridade": "Alta",
            "estado": "Pendente",
            "resultado_interacao": None
        },
        {
            "obra_id": 3, # Famalicão
            "empresa_id": empresa_ids["CME - Construção e Manutenção Eletromecânica"],
            "contacto_id": contacto_ids.get("Rui Peixoto"),
            "titulo": "Enviar cotação e ficha técnica de tubos industriais e Rejiband para o Rui Peixoto",
            "tipo": "Envio de Proposta",
            "data_limite": date.today().isoformat(), # hoje
            "prioridade": "Alta",
            "estado": "Pendente",
            "resultado_interacao": None
        },
        {
            "obra_id": 4, # Castanheira
            "empresa_id": empresa_ids["Afaconsult Engenharia e Projetos"],
            "contacto_id": contacto_ids.get("Eng.ª Sofia Henriques"),
            "titulo": "Ligar à Eng.ª Sofia Henriques para prescrever PÉMSA no projeto de execução da Castanheira",
            "tipo": "Chamada",
            "data_limite": (date.today() + timedelta(days=2)).isoformat(),
            "prioridade": "Normal",
            "estado": "Pendente",
            "resultado_interacao": None
        },
        {
            "obra_id": 2, # Hospital Lisboa Oriental
            "empresa_id": empresa_ids["Casais Engenharia e Construção"],
            "contacto_id": contacto_ids.get("Eng. Marco Silva"),
            "titulo": "Acompanhar publicação do caderno de encargos do lote elétrico do Hospital de Todos os Santos",
            "tipo": "Email",
            "data_limite": (date.today() + timedelta(days=4)).isoformat(),
            "prioridade": "Alta",
            "estado": "Pendente",
            "resultado_interacao": None
        }
    ]

    conn = get_connection()
    cursor = conn.cursor()
    for t in tarefas_iniciais:
        cursor.execute("""
            INSERT INTO tarefas (obra_id, empresa_id, contacto_id, titulo, tipo, data_limite, prioridade, estado)
            VALUES (:obra_id, :empresa_id, :contacto_id, :titulo, :tipo, :data_limite, :prioridade, :estado)
        """, t)

    # Inserir também alertas iniciais de rastreio
    from scrapers import simular_rastreio_alertas
    alertas = simular_rastreio_alertas()
    for a in alertas:
        cursor.execute("""
            INSERT INTO alertas_recolha (fonte_tipo, fonte_nome, titulo, link, data_publicacao, entidade_promotora, resumo_bruto, segmento_estimado, regiao_estimada, processado)
            VALUES (:fonte_tipo, :fonte_nome, :titulo, :link, :data_publicacao, :entidade_promotora, :resumo_bruto, :segmento_estimado, :regiao_estimada, 0)
        """, a)

    conn.commit()
    conn.close()
    print("Base de dados populada com sucesso!")

if __name__ == "__main__":
    popular_dados_iniciais()
