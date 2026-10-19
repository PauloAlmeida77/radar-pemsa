"""
seed_data.py - Popula a base de dados com projetos, empresas, contactos e tarefas realistas em Portugal.
"""

import json
from datetime import date, timedelta
from database import get_connection, init_db, inserir_obra
from scoring import calcular_score_obra

def popular_dados_iniciais():
    """Insere e atualiza dados reais de empresas, prioridades de contacto e obras em Portugal."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    # Verificar se já existem dados e atualizar sempre para contactos institucionais reais (sem nomes fictícios)
    cursor.execute("SELECT COUNT(*) FROM obras")
    if cursor.fetchone()[0] > 0:
        updates_obras = [
            (
                "PEMSA-2026-SINES",
                "1.ª Prioridade: Projetista MEP (Dep. Engenharia Eletrotécnica)",
                "Ligar 1.º ao Projetista (Prescrição CAD/BIM) | 2.º ao Instalador (Sotécnica)",
                "Projetista: Quadrante Engenharia | Instalador: Sotécnica | Promotor: Start Campus",
                "Quadrante: +351 217 998 210 (geral@quadrante-engenharia.pt) | Sotécnica: +351 219 829 200",
                "Ligar 1.º ao Dep. Eletrotécnico da Quadrante para prescrever Rejiband Rapide Black C8 e 2.º à Direção MEP da Sotécnica."
            ),
            (
                "PEMSA-2026-HLISBOA",
                "1.ª Prioridade: Construtor Adjudicatário (Direção de Instalações Especiais)",
                "Ligar 1.º ao Consórcio Construtor (Mota-Engil) | 2.º ao Projetista (Quadrante)",
                "Construtor: Mota-Engil Engenharia | Projetista MEP: Quadrante Engenharia",
                "Mota-Engil: +351 225 190 300 (geral@mota-engil.pt) | Quadrante: +351 217 998 210",
                "Contactar 1.º a Direção de Instalações Especiais da Mota-Engil e o gabinete Quadrante para especificar Pemsaband E90."
            ),
            (
                "PEMSA-2026-FAMALICAO",
                "1.ª Prioridade: Instalador Elétrico em Obra & Construtor Geral",
                "Obra Iniciada — Ligar 1.º ao Instalador Elétrico (CME) | 2.º ao Construtor (DST)",
                "Instalador: CME Eletromecânica | Construtor: DST Group | Promotor: Continental Mabor",
                "CME: +351 219 259 100 (cme@cme.pt) | DST Group: +351 253 307 200 (geral@dstsgps.com)",
                "Ligar 1.º ao Dep. de Compras / Obras Industriais da CME para cotar Rejiband Rapide e tubos metálicos via distribuidor."
            ),
            (
                "PEMSA-2026-CASTANHEIRA",
                "1.ª Prioridade: Projetista MEP (Instalações Elétricas)",
                "Fase de Projeto — Ligar 1.º ao Projetista (Afaconsult) | 2.º ao Promotor (Panattoni)",
                "Projetista MEP: Afaconsult Engenharia | Promotor: Panattoni Portugal",
                "Afaconsult Porto: +351 225 320 060 | Lisboa: +351 217 937 022 (geral@afaconsult.com)",
                "Ligar 1.º ao Dep. de Instalações Especiais da Afaconsult para incluir Rejiband no mapa de quantidades."
            ),
            (
                "PEMSA-2026-COMPORTA",
                "1.ª Prioridade: Construtor Geral (Direção de Compras e Produção MEP)",
                "Início de Construção — Ligar 1.º ao Construtor (Casais Engenharia)",
                "Construtor: Casais Engenharia e Construção | Promotor: Vanguard Properties",
                "Casais (Sede): +351 253 305 400 (geral@casais.pt) | Vanguard: +351 213 100 200",
                "Ligar 1.º à Direção de Produção MEP da Casais para apresentar gama PVC isolante e Inox 316L para ambiente marítimo."
            ),
            (
                "PEMSA-2026-MADEIRA",
                "1.ª Prioridade: Consórcio Construtor (Suprimentos de Instalações Técnicas)",
                "Em Obra — Ligar 1.º à Direção de Compras Técnicas do Construtor",
                "Construtor: Mota-Engil Engenharia (Consórcio Hospitalar Madeira)",
                "Mota-Engil: +351 225 190 300 (geral@mota-engil.pt)",
                "Articular com a Direção de Suprimentos da Mota-Engil e distribuidor parceiro no Funchal para fornecimento de Rejiband."
            ),
            (
                "PEMSA-2026-MAIA",
                "1.ª Prioridade: Projetista de Engenharia Elétrica / Instalador Norte",
                "Fase de Projeto — Ligar 1.º ao Gabinete Projetista MEP",
                "Projetista MEP: Gabinete de Engenharia Elétrica (Porto/Braga)",
                "Pesquisa direta LinkedIn (Engenharia Eletrotécnica Maia / Porto)",
                "Identificar e contactar 1.º o projetista elétrico para especificar Rejiband com resistência anticorrosiva para frio industrial."
            ),
            (
                "PEMSA-2026-CORUCHE",
                "1.ª Prioridade: Projetista MEP & Instalador de Data Centers",
                "Fase de Projeto — Ligar 1.º ao Projetista MEP (Quadrante) | 2.º ao Instalador (Sotécnica)",
                "Projetista MEP: Quadrante Engenharia | Instalador: Sotécnica (VINCI Energies)",
                "Quadrante: +351 217 998 210 (geral@quadrante-engenharia.pt) | Sotécnica: +351 219 829 200",
                "Ligar 1.º ao Dep. de Data Centers / Eletrotécnica da Quadrante e 2.º à Sotécnica para especificar Rejiband Rapide Black C8."
            ),
            (
                "PEMSA-2026-SOMFY",
                "1.ª Prioridade: Projetista Eletrotécnico & Construtor Industrial",
                "Fase de Projeto — Ligar 1.º ao Projetista (Afaconsult) | 2.º ao Construtor (DST) e Instalador (CME)",
                "Projetista: Afaconsult | Construtor: DST Group | Instalador: CME | Promotor: Somfy",
                "Afaconsult: +351 225 320 060 | DST: +351 253 307 200 | CME: +351 219 259 100",
                "Ligar 1.º à Afaconsult (Porto) e 2.º à CME/DST para prescrever Pemsaband PQX e tubos industriais na nova fábrica de Felgueiras."
            ),
            (
                "PEMSA-2026-LOGICOR",
                "1.ª Prioridade: Construtor Geral (Orçamentação MEP) & Instalador",
                "Fase de Concurso — Ligar 1.º ao Construtor (Casais) | 2.º ao Instalador (Sotécnica)",
                "Construtor: Casais Engenharia | Instalador: Sotécnica | Promotor: Logicor Portugal",
                "Casais: +351 253 305 400 (geral@casais.pt) | Sotécnica: +351 219 829 200 (geral@sotecnica.pt)",
                "Ligar 1.º ao Dep. de Orçamentação MEP da Casais e da Sotécnica para cotar caminhos de cabos da plataforma de 34.000 m²."
            ),
            (
                "PEMSA-2026-SOPHIA",
                "1.ª Prioridade: Projetista de Subestações & Construtor de Energia",
                "Fase SIAIA / Projeto — Ligar 1.º à Engenharia Elétrica | 2.º ao Construtor (Mota-Engil)",
                "Construtor / Engenharia: Mota-Engil Renovables & Gabinete de Engenharia Elétrica",
                "Mota-Engil: +351 225 190 300 (geral@mota-engil.pt)",
                "Ligar 1.º à equipa de Engenharia de Renováveis para especificar caminhos de cabos Galvanizados a Quente (HDG) nas subestações."
            ),
        ]
        for ref, n, c, e, cont, prox in updates_obras:
            cursor.execute("""
                UPDATE obras
                SET responsavel_nome = ?, responsavel_cargo = ?, responsavel_empresa = ?, responsavel_contacto = ?, proxima_acao = ?
                WHERE codigo_ref = ?
            """, (n, c, e, cont, prox, ref))

        # Atualizar contactos das empresas com telefones reais de sede
        updates_empresas = [
            ("Quadrante Engenharia & MEP", "+351 217 998 210", "geral@quadrante-engenharia.pt", "https://www.quadrante-engenharia.pt"),
            ("Afaconsult Engenharia e Projetos", "+351 225 320 060", "geral@afaconsult.com", "https://www.afaconsult.com"),
            ("Casais Engenharia e Construção", "+351 253 305 400", "geral@casais.pt", "https://www.casais.pt"),
            ("Mota-Engil Engenharia", "+351 225 190 300", "geral@mota-engil.pt", "https://www.mota-engil.pt"),
            ("DST Group (Domingos da Silva Teixeira)", "+351 253 307 200", "geral@dstsgps.com", "https://www.dstsgps.com"),
            ("Sotécnica - VINCI Energies Portugal", "+351 219 829 200", "geral@sotecnica.pt", "https://www.sotecnica.pt"),
            ("CME - Construção e Manutenção Eletromecânica", "+351 219 259 100", "cme@cme.pt", "https://www.cme.pt"),
        ]
        for nome_e, tel_e, em_e, web_e in updates_empresas:
            cursor.execute("""
                UPDATE empresas SET telefone = ?, email = ?, website = ? WHERE nome = ?
            """, (tel_e, em_e, web_e, nome_e))

        # Substituir contactos fictícios na tabela contactos por departamentos reais
        cursor.execute("DELETE FROM contactos WHERE nome IN ('Eng. Tiago Mendonça', 'Eng.ª Sofia Henriques', 'Carlos Fonseca', 'Rui Peixoto', 'Eng. Marco Silva')")
        cursor.execute("SELECT COUNT(*) FROM contactos")
        if cursor.fetchone()[0] == 0:
            cursor.execute("SELECT id, nome FROM empresas")
            emp_map = {r["nome"]: r["id"] for r in cursor.fetchall()}
            contactos_reais = [
                ("Quadrante Engenharia & MEP", "Dep. Engenharia Eletrotécnica & Data Centers (Quadrante)", "1.ª Prioridade em Fase de Projeto (Prescrição Técnica)", "Instalações Especiais / MEP", "+351 217 998 210", "geral@quadrante-engenharia.pt", "https://www.linkedin.com/search/results/people/?keywords=Quadrante%20Engenharia%20Eletrotecnica", "Ligar para a sede e pedir passagem ao coordenador de Eletrotécnica do projeto, ou pesquisar diretamente no LinkedIn."),
                ("Afaconsult Engenharia e Projetos", "Dep. Instalações Especiais / Eletrotécnica (Afaconsult)", "1.ª Prioridade em Fase de Projeto (Prescrição Técnica)", "Engenharia MEP", "+351 225 320 060", "geral@afaconsult.com", "https://www.linkedin.com/search/results/people/?keywords=Afaconsult%20Eletrotecnica", "Escritórios no Porto (+351 225 320 060) e Lisboa (+351 217 937 022)."),
                ("Sotécnica - VINCI Energies Portugal", "Direção de Compras e Orçamentação MEP (Sotécnica)", "1.ª Prioridade em Concurso e Execução Elétrica", "Compras / Orçamentação", "+351 219 829 200", "geral@sotecnica.pt", "https://www.linkedin.com/search/results/people/?keywords=Sotecnica%20Orcamentacao%20Compras", "Instalador elétrico de referência para Data Centers, Indústria e Hospitais."),
                ("CME - Construção e Manutenção Eletromecânica", "Direção de Obras e Instalações Industriais (CME)", "1.ª Prioridade em Concurso e Obra Elétrica", "Direção de Produção Elétrica", "+351 219 259 100", "cme@cme.pt", "https://www.linkedin.com/search/results/people/?keywords=CME%20Instalacoes%20Eletricas", "Forte presença em instalações elétricas industriais e redes."),
                ("Casais Engenharia e Construção", "Direção de Produção MEP e Compras (Grupo Casais)", "1.ª Prioridade em Empreitadas Gerais Adjudicadas", "Compras / Instalações Especiais", "+351 253 305 400", "geral@casais.pt", "https://www.linkedin.com/search/results/people/?keywords=Casais%20Engenharia%20MEP", "Construtor geral; coordena subempreitadas de instalações elétricas e mecânicas."),
                ("Mota-Engil Engenharia", "Direção de Suprimentos e Instalações Especiais (Mota-Engil)", "1.ª Prioridade em Grandes Concursos Públicos", "Suprimentos / MEP", "+351 225 190 300", "geral@mota-engil.pt", "https://www.linkedin.com/search/results/people/?keywords=Mota%20Engil%20Instalacoes%20Especiais", "Líder em grandes obras hospitalares, ferroviárias e infraestruturas."),
                ("DST Group (Domingos da Silva Teixeira)", "Direção de Compras e DSTELE (Grupo DST)", "1.ª Prioridade em Obras Industriais e Logística", "Compras / Eletricidade", "+351 253 307 200", "geral@dstsgps.com", "https://www.linkedin.com/search/results/people/?keywords=DST%20DSTELE%20Engenharia", "Construtor de referência no Norte para unidades fabris e plataformas logísticas.")
            ]
            for emp_n, nom, car, dep, tel, em, lnk, nots in contactos_reais:
                eid = emp_map.get(emp_n)
                if eid:
                    cursor.execute("""
                        INSERT INTO contactos (empresa_id, nome, cargo, departamento, telefone, email, linkedin, notas)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (eid, nom, car, dep, tel, em, lnk, nots))

        # Limpar nomes fictícios nas tarefas existentes
        cursor.execute("UPDATE tarefas SET titulo = REPLACE(titulo, 'ao Eng. Tiago Mendonça', 'ao Projetista MEP (Quadrante) e Instalador (Sotécnica)')")
        cursor.execute("UPDATE tarefas SET titulo = REPLACE(titulo, 'para o Rui Peixoto', 'para o Dep. de Obras Elétricas da CME e Construtor DST')")
        cursor.execute("UPDATE tarefas SET titulo = REPLACE(titulo, 'à Eng.ª Sofia Henriques', 'ao Dep. de Eletrotécnica da Afaconsult')")
        cursor.execute("UPDATE tarefas SET titulo = REPLACE(titulo, 'com Eng. Marco Silva', 'com a Direção de Produção MEP da Casais')")

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

    # 2. Inserir Contactos Institucionais Reais e Departamentos Prioritários
    contactos = [
        {"empresa_nome": "Quadrante Engenharia & MEP", "nome": "Departamento de Instalações Especiais / Eletrotécnica (Quadrante)", "cargo": "1.ª Prioridade em Fase de Projeto MEP", "departamento": "Engenharia Elétrica & Data Centers", "telefone": "+351 217 998 210", "email": "geral@quadrante-engenharia.pt", "linkedin": "https://www.linkedin.com/search/results/people/?keywords=Quadrante%20Engenharia%20Eletrotecnica", "notas": "Pedir na receção (+351 217 998 210) pelo Coordenador de Eletrotécnica / Instalações Especiais da obra em causa."},
        {"empresa_nome": "Afaconsult Engenharia e Projetos", "nome": "Departamento de Engenharia Eletrotécnica e MEP (Afaconsult)", "cargo": "1.ª Prioridade em Fase de Projeto MEP", "departamento": "Instalações Especiais (Porto / Lisboa)", "telefone": "+351 225 320 060", "email": "geral@afaconsult.com", "linkedin": "https://www.linkedin.com/search/results/people/?keywords=Afaconsult%20Engenharia%20Eletrotecnica", "notas": "Escritório Porto (+351 225 320 060) / Escritório Lisboa (+351 217 937 022). Solicitar equipa de projeto MEP."},
        {"empresa_nome": "Sotécnica - VINCI Energies Portugal", "nome": "Direção de Compras e Orçamentação MEP (Sotécnica)", "cargo": "1.ª Prioridade em Concurso e Execução Elétrica", "departamento": "Compras / Orçamentação", "telefone": "+351 219 829 200", "email": "geral@sotecnica.pt", "linkedin": "https://www.linkedin.com/search/results/people/?keywords=Sotecnica%20Orcamentacao%20Compras", "notas": "Instalador elétrico de referência para Data Centers, Indústria e Hospitais."},
        {"empresa_nome": "CME - Construção e Manutenção Eletromecânica", "nome": "Direção de Obras e Instalações Industriais (CME)", "cargo": "1.ª Prioridade em Concurso e Obra Elétrica", "departamento": "Direção de Produção Elétrica", "telefone": "+351 219 259 100", "email": "cme@cme.pt", "linkedin": "https://www.linkedin.com/search/results/people/?keywords=CME%20Instalacoes%20Eletricas", "notas": "Forte presença em instalações elétricas industriais e redes."},
        {"empresa_nome": "Casais Engenharia e Construção", "nome": "Direção de Produção MEP e Compras (Grupo Casais)", "cargo": "1.ª Prioridade em Empreitadas Gerais Adjudicadas", "departamento": "Compras / Instalações Especiais", "telefone": "+351 253 305 400", "email": "geral@casais.pt", "linkedin": "https://www.linkedin.com/search/results/people/?keywords=Casais%20Engenharia%20MEP", "notas": "Construtor geral; coordena subempreitadas de instalações elétricas e mecânicas."}
    ]

    contacto_ids = {}
    for c in contactos:
        emp_id = empresa_ids.get(c["empresa_nome"])
        if emp_id:
            cursor.execute("""
                INSERT INTO contactos (empresa_id, nome, cargo, departamento, telefone, email, linkedin, notas)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (emp_id, c["nome"], c["cargo"], c["departamento"], c["telefone"], c["email"], c["linkedin"], c["notas"]))
            contacto_ids[c["empresa_nome"]] = cursor.lastrowid

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
                "proxima_acao": "1.º Ligar ao Projetista MEP (Quadrante) para especificar Rejiband Rapide Black C8 no caderno de encargos; 2.º Articular com a Direção de Compras da Sotécnica (Instalador).",
                "notas_comerciais": "Oportunidade de topo a nível ibérico. O volume previsto de caminhos de cabos ultrapassa os 40.000 metros lineares.",
                "responsavel_nome": "1.ª Prioridade: Ligar 1.º ao Projetista MEP (Dep. Instalações Especiais)",
                "responsavel_cargo": "2.ª Prioridade: Instalador Elétrico / Compras MEP",
                "responsavel_empresa": "Projetista: Quadrante Engenharia | Instalador: Sotécnica (VINCI) | Promotor: Start Campus",
                "responsavel_contacto": "Quadrante (Geral): +351 217 998 210 | geral@quadrante-engenharia.pt • Sotécnica: +351 219 829 200"
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
                "proxima_acao": "1.º Ligar ao Dep. de Compras/Orçamentação dos Construtores (Mota-Engil e Casais); 2.º Validar conformidade técnica E90 com o Projetista (Quadrante).",
                "notas_comerciais": "Projeto crítico de contratação pública. Homologações de segurança contra incêndios da PÉMSA são um fator diferenciador.",
                "responsavel_nome": "1.ª Prioridade: Ligar 1.º ao Construtor (Dep. Orçamentação / Compras MEP)",
                "responsavel_cargo": "2.ª Prioridade: Projetista MEP (Validação de Equivalências E90)",
                "responsavel_empresa": "Construtor: Mota-Engil / Casais | Projetista MEP: Quadrante Engenharia",
                "responsavel_contacto": "Mota-Engil: +351 225 190 300 | Casais: +351 253 305 400 | Quadrante: +351 217 998 210"
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
                "proxima_acao": "1.º Ligar ao Dep. de Compras / Direção de Obra da CME (Instalador Elétrico) para cotar Rejiband e tubos industriais; 2.º Acompanhar com o Construtor DST Group.",
                "notas_comerciais": "Estão recetivos ao sistema de encaixe rápido Rejiband Rapide devido ao prazo apertado da obra.",
                "responsavel_nome": "1.ª Prioridade: Ligar 1.º ao Instalador Elétrico (Direção de Obra / Compras)",
                "responsavel_cargo": "2.ª Prioridade: Construtor Geral (Direção de Produção)",
                "responsavel_empresa": "Instalador Elétrico: CME | Construtor Geral: DST Group | Dono: Continental Mabor",
                "responsavel_contacto": "CME (Geral): +351 219 259 100 | cme@cme.pt • DST Group (Braga): +351 253 307 200"
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
                "proxima_acao": "1.º Ligar ao Dep. de Engenharia Eletrotécnica da Afaconsult (Projetista) para prescrever Rejiband no mapa de quantidades antes do lançamento a empreitada.",
                "notas_comerciais": "Projetistas da Afaconsult conhecem bem a PÉMSA. Promotor pan-europeu com dezenas de armazéns na Península Ibérica.",
                "responsavel_nome": "1.ª Prioridade: Ligar 1.º ao Projetista MEP (Dep. Eletrotécnico)",
                "responsavel_cargo": "2.ª Prioridade: Promotor Imobiliário (Gestão de Projeto)",
                "responsavel_empresa": "Projetista MEP: Afaconsult | Promotor: Panattoni Portugal | Construtor: Em Concurso",
                "responsavel_contacto": "Afaconsult: +351 225 320 060 / +351 217 937 022 | geral@afaconsult.com"
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
                "proxima_acao": "1.º Ligar à Direção de Compras / Instalações Especiais da Casais (Construtor) para apresentar gama PVC isolante e Inox 316L para ambiente marítimo.",
                "notas_comerciais": "Excelente montra para a gama de PVC isolante e acabamento Inox 316L da PÉMSA.",
                "responsavel_nome": "1.ª Prioridade: Ligar 1.º ao Construtor (Direção de Compras / Produção MEP)",
                "responsavel_cargo": "2.ª Prioridade: Subempreiteiro de Instalações Elétricas",
                "responsavel_empresa": "Construtor Geral: Casais Engenharia e Construção | Promotor: Vanguard Properties",
                "responsavel_contacto": "Grupo Casais (Geral): +351 253 305 400 | geral@casais.pt"
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
                "proxima_acao": "1.º Contactar Direção de Suprimentos MEP do Consórcio Construtor (Mota-Engil) e articular stock local de Rejiband no Funchal.",
                "notas_comerciais": "Logística marítima requer planeamento de 2 semanas de antecedência.",
                "responsavel_nome": "1.ª Prioridade: Ligar 1.º ao Construtor / Direção de Obra MEP",
                "responsavel_cargo": "2.ª Prioridade: Distribuidor Elétrico Local (Madeira)",
                "responsavel_empresa": "Construtor Geral: Consórcio Mota-Engil Engenharia",
                "responsavel_contacto": "Mota-Engil (Geral): +351 225 190 300 | geral@mota-engil.pt"
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
                "proxima_acao": "1.º Ligar ao Projetista Elétrico (Projenel / Gabinete MEP no Norte) para especificar Rejiband com proteção anticorrosiva em câmaras de frio.",
                "notas_comerciais": "Excelente localização no Porto/Norte com contacto rápido.",
                "responsavel_nome": "1.ª Prioridade: Ligar 1.º ao Projetista de Instalações Elétricas",
                "responsavel_cargo": "2.ª Prioridade: Instalador de Frio e Eletricidade Industrial",
                "responsavel_empresa": "Projetista MEP: Projenel Projetos Elétricos | Instalador: Instalectra",
                "responsavel_contacto": "Projenel (Braga): +351 253 200 400 | geral@projenel.pt"
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
            "contacto_id": contacto_ids.get("Quadrante Engenharia & MEP"),
            "titulo": "Apresentar Rejiband Rapide Black C8 ao Projetista MEP (Quadrante) e Instalador (Sotécnica) (Data Center Sines)",
            "tipo": "Apresentação Técnica",
            "data_limite": (date.today() - timedelta(days=1)).isoformat(), # em atraso para alertar
            "prioridade": "Alta",
            "estado": "Pendente",
            "resultado_interacao": None
        },
        {
            "obra_id": 3, # Famalicão
            "empresa_id": empresa_ids["CME - Construção e Manutenção Eletromecânica"],
            "contacto_id": contacto_ids.get("CME - Construção e Manutenção Eletromecânica"),
            "titulo": "Enviar cotação e ficha técnica de tubos industriais e Rejiband para o Dep. de Obras Elétricas da CME e Construtor DST",
            "tipo": "Envio de Proposta",
            "data_limite": date.today().isoformat(), # hoje
            "prioridade": "Alta",
            "estado": "Pendente",
            "resultado_interacao": None
        },
        {
            "obra_id": 4, # Castanheira
            "empresa_id": empresa_ids["Afaconsult Engenharia e Projetos"],
            "contacto_id": contacto_ids.get("Afaconsult Engenharia e Projetos"),
            "titulo": "Ligar ao Dep. de Eletrotécnica da Afaconsult para prescrever PÉMSA no projeto de execução da Castanheira",
            "tipo": "Chamada",
            "data_limite": (date.today() + timedelta(days=2)).isoformat(),
            "prioridade": "Normal",
            "estado": "Pendente",
            "resultado_interacao": None
        },
        {
            "obra_id": 2, # Hospital Lisboa Oriental
            "empresa_id": empresa_ids["Casais Engenharia e Construção"],
            "contacto_id": contacto_ids.get("Casais Engenharia e Construção"),
            "titulo": "Acompanhar publicação do caderno de encargos do lote elétrico do Hospital de Todos os Santos (Mota-Engil / Casais)",
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
