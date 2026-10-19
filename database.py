"""
database.py - Módulo de gestão da base de dados SQLite do Radar de Obras PÉMSA.
"""

import sqlite3
import os
import sys
import json
from datetime import datetime, date

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

DB_PATH = os.path.join(CURRENT_DIR, "radar_pemsa.db")

def get_connection():
    """Obtém uma conexão à base de dados SQLite."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa as tabelas da base de dados se não existirem."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Tabela de Obras
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS obras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        codigo_ref TEXT UNIQUE,
        segmento TEXT NOT NULL,
        regiao TEXT NOT NULL,
        distrito TEXT NOT NULL,
        concelho TEXT,
        morada_localizacao TEXT,
        lat REAL,
        lon REAL,
        fase TEXT NOT NULL,
        status_comercial TEXT DEFAULT 'Nova Oportunidade',
        score INTEGER DEFAULT 0,
        score_breakdown TEXT,
        prioridade TEXT DEFAULT 'Média',
        valor_estimado TEXT,
        prazo_previsto TEXT,
        data_detecao DATE,
        fonte_tipo TEXT,
        fonte_nome TEXT,
        fonte_url TEXT,
        resumo TEXT,
        timing_fornecimento TEXT,
        proxima_acao TEXT,
        notas_comerciais TEXT,
        responsavel_nome TEXT,
        responsavel_cargo TEXT,
        responsavel_empresa TEXT,
        responsavel_contacto TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Migração automática se a tabela já existir sem estas colunas
    cursor.execute("PRAGMA table_info(obras)")
    colunas_existentes = [col[1] for col in cursor.fetchall()]
    for col_n, col_t in [
        ("responsavel_nome", "TEXT"),
        ("responsavel_cargo", "TEXT"),
        ("responsavel_empresa", "TEXT"),
        ("responsavel_contacto", "TEXT")
    ]:
        if col_n not in colunas_existentes:
            cursor.execute(f"ALTER TABLE obras ADD COLUMN {col_n} {col_t}")

    # 2. Tabela de Empresas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS empresas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        nif TEXT,
        tipo TEXT NOT NULL, -- Promotor, Projetista MEP, Empreiteiro Geral, Instalador Elétrico, Distribuidor
        distrito TEXT,
        cidade TEXT,
        morada TEXT,
        telefone TEXT,
        email TEXT,
        website TEXT,
        nivel_relacionamento TEXT DEFAULT 'Sem Contacto', -- Sem Contacto, Contacto Frio, Parceiro Habitual, Cliente Ativo
        notas TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 3. Tabela de Intervenientes na Obra (relação Obra <-> Empresa)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS obra_empresas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        obra_id INTEGER NOT NULL,
        empresa_id INTEGER NOT NULL,
        papel TEXT NOT NULL, -- Promotor/Dono, Projetista MEP, Empreiteiro Geral, Instalador Elétrico, Comprador/Distribuidor
        confirmado INTEGER DEFAULT 1,
        notas TEXT,
        FOREIGN KEY (obra_id) REFERENCES obras (id) ON DELETE CASCADE,
        FOREIGN KEY (empresa_id) REFERENCES empresas (id) ON DELETE CASCADE,
        UNIQUE(obra_id, empresa_id, papel)
    )
    """)

    # 4. Tabela de Contactos de Pessoas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contactos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        nome TEXT NOT NULL,
        cargo TEXT,
        departamento TEXT,
        telefone TEXT,
        email TEXT,
        linkedin TEXT,
        notas TEXT,
        FOREIGN KEY (empresa_id) REFERENCES empresas (id) ON DELETE CASCADE
    )
    """)

    # 5. Tabela de Produtos PÉMSA na Obra
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS obra_produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        obra_id INTEGER NOT NULL,
        familia_produto TEXT NOT NULL,
        nivel_potencial TEXT DEFAULT 'Potencial Teórico', -- Potencial Teórico, Compatibilidade Confirmada, Oportunidade Validada
        especificacao_detalhe TEXT,
        incluido INTEGER DEFAULT 1,
        FOREIGN KEY (obra_id) REFERENCES obras (id) ON DELETE CASCADE
    )
    """)

    # 6. Tabela de Tarefas e Histórico Comercial
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tarefas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        obra_id INTEGER,
        empresa_id INTEGER,
        contacto_id INTEGER,
        titulo TEXT NOT NULL,
        tipo TEXT NOT NULL, -- Chamada, Email, Visita/Reunião, Apresentação Técnica, Envio de Amostras, Envio de Proposta
        data_limite DATE NOT NULL,
        prioridade TEXT DEFAULT 'Normal',
        estado TEXT DEFAULT 'Pendente', -- Pendente, Concluída, Cancelada
        resultado_interacao TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_conclusao TIMESTAMP,
        FOREIGN KEY (obra_id) REFERENCES obras (id) ON DELETE CASCADE,
        FOREIGN KEY (empresa_id) REFERENCES empresas (id) ON DELETE SET NULL,
        FOREIGN KEY (contacto_id) REFERENCES contactos (id) ON DELETE SET NULL
    )
    """)

    # 7. Tabela de Feed de Alertas / Rastreio Bruto
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alertas_recolha (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fonte_tipo TEXT NOT NULL,
        fonte_nome TEXT NOT NULL,
        titulo TEXT NOT NULL,
        link TEXT,
        data_publicacao DATE,
        entidade_promotora TEXT,
        resumo_bruto TEXT,
        segmento_estimado TEXT,
        regiao_estimada TEXT,
        processado INTEGER DEFAULT 0,
        obra_id_gerada INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 8. Tabela de Configurações e Estado do Sistema
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracoes (
        chave TEXT PRIMARY KEY,
        valor TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def obter_config(chave, default=None):
    """Obtém uma chave de configuração."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else default

def definir_config(chave, valor):
    """Define ou atualiza uma chave de configuração."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        INSERT INTO configuracoes (chave, valor, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor, updated_at=CURRENT_TIMESTAMP
    """, (chave, str(valor)))
    conn.commit()
    conn.close()

def verificar_e_executar_sincronizacao_automatica(forcar=False):
    """
    Verifica se já passou a periodicidade de atualização semanal (todas as segundas-feiras / nova semana ISO)
    ou se faltam as obras da atualização semanal atual.
    Insere novas obras qualificadas no Radar (tabela obras), cria tarefas e recolhe alertas em tempo real via RSS.
    """
    from datetime import timedelta
    from scrapers import simular_rastreio_alertas, obter_obras_atualizacao_semanal

    ultima_sync = obter_config("ultima_sincronizacao")
    ultima_semana = obter_config("ultima_semana_sync")
    hoje = date.today().isoformat()
    iso_cal = date.today().isocalendar()
    semana_atual = f"{iso_cal[0]}-W{iso_cal[1]:02d}"

    deve_atualizar = forcar

    if not ultima_sync or ultima_semana != semana_atual:
        deve_atualizar = True
    else:
        try:
            dt_ult = date.fromisoformat(ultima_sync)
            dias_passados = (date.today() - dt_ult).days
            if dias_passados >= 7 or (date.today().weekday() == 0 and dt_ult != date.today()):
                deve_atualizar = True
        except Exception:
            deve_atualizar = True

    # Garantir que as obras do lote semanal atual estão presentes na tabela obras
    obras_semanais = obter_obras_atualizacao_semanal()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT codigo_ref FROM obras WHERE codigo_ref = ?", ("PEMSA-2026-CORUCHE",))
    if not cur.fetchone():
        deve_atualizar = True
    conn.close()

    if deve_atualizar:
        conn = get_connection()
        cur = conn.cursor()
        obras_inseridas = 0
        alertas_inseridos = 0

        # Mapear empresas existentes por nome
        cur.execute("SELECT id, nome FROM empresas")
        mapa_empresas = {r["nome"]: r["id"] for r in cur.fetchall()}

        # 1. Inserir novas obras qualificadas da semana diretamente no Radar (tabela obras)
        for item in obras_semanais:
            dados_o = item["obra"]
            cur.execute("SELECT id FROM obras WHERE codigo_ref = ? OR titulo = ?", (dados_o["codigo_ref"], dados_o["titulo"]))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO obras (
                        titulo, codigo_ref, segmento, regiao, distrito, concelho, morada_localizacao,
                        lat, lon, fase, status_comercial, score, score_breakdown, prioridade,
                        valor_estimado, prazo_previsto, data_detecao, fonte_tipo, fonte_nome,
                        fonte_url, resumo, timing_fornecimento, proxima_acao, notas_comerciais,
                        responsavel_nome, responsavel_cargo, responsavel_empresa, responsavel_contacto
                    ) VALUES (
                        :titulo, :codigo_ref, :segmento, :regiao, :distrito, :concelho, :morada_localizacao,
                        :lat, :lon, :fase, :status_comercial, :score, :score_breakdown, :prioridade,
                        :valor_estimado, :prazo_previsto, :data_detecao, :fonte_tipo, :fonte_nome,
                        :fonte_url, :resumo, :timing_fornecimento, :proxima_acao, :notas_comerciais,
                        :responsavel_nome, :responsavel_cargo, :responsavel_empresa, :responsavel_contacto
                    )
                """, dados_o)
                nova_obra_id = cur.lastrowid
                obras_inseridas += 1

                # Associar empresas
                for emp_rel in item.get("empresas", []):
                    emp_id = mapa_empresas.get(emp_rel["nome"])
                    if emp_id:
                        cur.execute("""
                            INSERT OR IGNORE INTO obra_empresas (obra_id, empresa_id, papel, confirmado, notas)
                            VALUES (?, ?, ?, 1, 'Associado na sincronização semanal')
                        """, (nova_obra_id, emp_id, emp_rel["papel"]))

                # Associar produtos PÉMSA
                for prod in item.get("produtos", []):
                    cur.execute("""
                        INSERT INTO obra_produtos (obra_id, familia_produto, nivel_potencial, especificacao_detalhe)
                        VALUES (?, ?, ?, ?)
                    """, (nova_obra_id, prod["familia_produto"], prod["nivel_potencial"], prod["especificacao_detalhe"]))

                # Criar tarefa comercial para a semana
                tar = item.get("tarefa")
                if tar:
                    prazo_tar = (date.today() + timedelta(days=3)).isoformat()
                    cur.execute("""
                        INSERT INTO tarefas (obra_id, titulo, tipo, data_limite, prioridade, estado)
                        VALUES (?, ?, ?, ?, ?, 'Pendente')
                    """, (nova_obra_id, tar["titulo"], tar["tipo"], prazo_tar, tar["prioridade"]))

        # 2. Recolher alertas e notícias reais via RSS para a caixa de entrada do Motor de Recolha
        novos_alertas = simular_rastreio_alertas()
        for n in novos_alertas:
            cur.execute("SELECT id FROM alertas_recolha WHERE titulo = ?", (n['titulo'],))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO alertas_recolha (
                        fonte_tipo, fonte_nome, titulo, link, data_publicacao,
                        entidade_promotora, resumo_bruto, segmento_estimado, regiao_estimada, processado
                    ) VALUES (
                        :fonte_tipo, :fonte_nome, :titulo, :link, :data_publicacao,
                        :entidade_promotora, :resumo_bruto, :segmento_estimado, :regiao_estimada, 0
                    )
                """, n)
                alertas_inseridos += 1

        conn.commit()
        conn.close()
        definir_config("ultima_sincronizacao", hoje)
        definir_config("ultima_semana_sync", semana_atual)
        definir_config("obras_adicionadas_semana", str(obras_inseridas if obras_inseridas > 0 else len(obras_semanais)))
        return True, (obras_inseridas + alertas_inseridos)

    return False, 0

# ----------------- OPERAÇÕES DE CONSULTA (READ) -----------------

def listar_obras(segmento=None, regiao=None, fase=None, prioridade=None, status_comercial=None, busca=None):
    """Retorna uma lista de obras com filtros opcionais."""
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM obras WHERE 1=1"
    params = []

    if segmento and segmento != "Todos":
        query += " AND segmento = ?"
        params.append(segmento)
    if regiao and regiao != "Todas":
        query += " AND regiao = ?"
        params.append(regiao)
    if fase and fase != "Todas":
        query += " AND fase = ?"
        params.append(fase)
    if prioridade and prioridade != "Todas":
        query += " AND prioridade = ?"
        params.append(prioridade)
    if status_comercial and status_comercial != "Todos":
        query += " AND status_comercial = ?"
        params.append(status_comercial)
    if busca:
        busca_term = f"%{busca}%"
        query += " AND (titulo LIKE ? OR concelho LIKE ? OR distrito LIKE ? OR resumo LIKE ?)"
        params.extend([busca_term, busca_term, busca_term, busca_term])

    query += " ORDER BY score DESC, created_at DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def obter_obra_por_id(obra_id):
    """Obtém os detalhes completos de uma obra."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM obras WHERE id = ?", (obra_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    obra = dict(row)

    # Buscar empresas intervenientes
    cursor.execute("""
        SELECT e.*, oe.papel, oe.confirmado, oe.notas as rel_notas
        FROM empresas e
        JOIN obra_empresas oe ON e.id = oe.empresa_id
        WHERE oe.obra_id = ?
        ORDER BY oe.papel ASC
    """, (obra_id,))
    obra['empresas'] = [dict(r) for r in cursor.fetchall()]

    # Buscar produtos PÉMSA
    cursor.execute("SELECT * FROM obra_produtos WHERE obra_id = ?", (obra_id,))
    obra['produtos'] = [dict(r) for r in cursor.fetchall()]

    # Buscar tarefas associadas
    cursor.execute("""
        SELECT t.*, e.nome as empresa_nome, c.nome as contacto_nome
        FROM tarefas t
        LEFT JOIN empresas e ON t.empresa_id = e.id
        LEFT JOIN contactos c ON t.contacto_id = c.id
        WHERE t.obra_id = ?
        ORDER BY t.data_limite ASC
    """, (obra_id,))
    obra['tarefas'] = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return obra

def listar_empresas(tipo=None, busca=None):
    """Lista empresas cadastradas com filtros."""
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM empresas WHERE 1=1"
    params = []
    if tipo and tipo != "Todos":
        query += " AND tipo = ?"
        params.append(tipo)
    if busca:
        b = f"%{busca}%"
        query += " AND (nome LIKE ? OR distrito LIKE ? OR cidade LIKE ?)"
        params.extend([b, b, b])
    query += " ORDER BY nome ASC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]

    for row in rows:
        cursor.execute("SELECT * FROM contactos WHERE empresa_id = ?", (row['id'],))
        row['contactos'] = [dict(c) for c in cursor.fetchall()]
        cursor.execute("""
            SELECT o.id, o.titulo, oe.papel
            FROM obras o
            JOIN obra_empresas oe ON o.id = oe.obra_id
            WHERE oe.empresa_id = ?
        """, (row['id'],))
        row['obras_participa'] = [dict(o) for o in cursor.fetchall()]

    conn.close()
    return rows

def listar_tarefas(apenas_pendentes=True):
    """Lista tarefas comerciais com informação da obra e contacto."""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT t.*, o.titulo as obra_titulo, o.score as obra_score,
               e.nome as empresa_nome, c.nome as contacto_nome, c.telefone as contacto_telefone
        FROM tarefas t
        LEFT JOIN obras o ON t.obra_id = o.id
        LEFT JOIN empresas e ON t.empresa_id = e.id
        LEFT JOIN contactos c ON t.contacto_id = c.id
    """
    if apenas_pendentes:
        query += " WHERE t.estado = 'Pendente'"
    query += " ORDER BY t.data_limite ASC, t.prioridade DESC"
    cursor.execute(query)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def listar_alertas(apenas_nao_processados=False):
    """Lista itens de recolha/alertas detetados."""
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM alertas_recolha"
    if apenas_nao_processados:
        query += " WHERE processado = 0"
    query += " ORDER BY data_publicacao DESC, id DESC"
    cursor.execute(query)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def obter_estatisticas_kpi():
    """Retorna métricas chave para o painel principal."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM obras")
    total_obras = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM obras WHERE score >= 75")
    prioritarias = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(DISTINCT o.id) FROM obras o
        WHERE NOT EXISTS (
            SELECT 1 FROM obra_empresas oe
            JOIN contactos c ON oe.empresa_id = c.empresa_id
            WHERE oe.obra_id = o.id
        )
    """)
    contactos_por_identificar = cursor.fetchone()[0]

    today = date.today().isoformat()
    cursor.execute("SELECT COUNT(*) FROM tarefas WHERE estado = 'Pendente' AND data_limite < ?", (today,))
    tarefas_atrasadas = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tarefas WHERE estado = 'Pendente' AND data_limite = ?", (today,))
    tarefas_hoje = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alertas_recolha WHERE processado = 0")
    alertas_novos = cursor.fetchone()[0]

    conn.close()
    return {
        "total_obras": total_obras,
        "prioritarias": prioritarias,
        "contactos_por_identificar": contactos_por_identificar,
        "tarefas_atrasadas": tarefas_atrasadas,
        "tarefas_hoje": tarefas_hoje,
        "alertas_novos": alertas_novos
    }

# ----------------- OPERAÇÕES DE ESCRITA / EDIÇÃO -----------------

def inserir_obra(dados_obra, empresas_intervenientes=None, produtos_pemsa=None):
    """Insere uma nova obra com cálculo de integridade."""
    conn = get_connection()
    cursor = conn.cursor()

    dados_obra.setdefault("responsavel_nome", None)
    dados_obra.setdefault("responsavel_cargo", None)
    dados_obra.setdefault("responsavel_empresa", None)
    dados_obra.setdefault("responsavel_contacto", None)

    cursor.execute("""
    INSERT INTO obras (
        titulo, codigo_ref, segmento, regiao, distrito, concelho, morada_localizacao,
        lat, lon, fase, status_comercial, score, score_breakdown, prioridade,
        valor_estimado, prazo_previsto, data_detecao, fonte_tipo, fonte_nome,
        fonte_url, resumo, timing_fornecimento, proxima_acao, notas_comerciais,
        responsavel_nome, responsavel_cargo, responsavel_empresa, responsavel_contacto
    ) VALUES (
        :titulo, :codigo_ref, :segmento, :regiao, :distrito, :concelho, :morada_localizacao,
        :lat, :lon, :fase, :status_comercial, :score, :score_breakdown, :prioridade,
        :valor_estimado, :prazo_previsto, :data_detecao, :fonte_tipo, :fonte_nome,
        :fonte_url, :resumo, :timing_fornecimento, :proxima_acao, :notas_comerciais,
        :responsavel_nome, :responsavel_cargo, :responsavel_empresa, :responsavel_contacto
    )
    """, dados_obra)
    obra_id = cursor.lastrowid

    if empresas_intervenientes:
        for item in empresas_intervenientes:
            cursor.execute("""
            INSERT OR IGNORE INTO obra_empresas (obra_id, empresa_id, papel, confirmado, notas)
            VALUES (?, ?, ?, ?, ?)
            """, (obra_id, item['empresa_id'], item['papel'], item.get('confirmado', 1), item.get('notas', '')))

    if produtos_pemsa:
        for p in produtos_pemsa:
            cursor.execute("""
            INSERT INTO obra_produtos (obra_id, familia_produto, nivel_potencial, especificacao_detalhe)
            VALUES (?, ?, ?, ?)
            """, (obra_id, p['familia_produto'], p.get('nivel_potencial', 'Potencial Teórico'), p.get('especificacao_detalhe', '')))

    conn.commit()
    conn.close()
    return obra_id

def atualizar_status_obra(obra_id, novo_status, novas_notas=None):
    """Atualiza o estado de pipeline de uma obra."""
    conn = get_connection()
    cursor = conn.cursor()
    if novas_notas:
        cursor.execute("""
            UPDATE obras SET status_comercial = ?, notas_comerciais = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (novo_status, novas_notas, obra_id))
    else:
        cursor.execute("""
            UPDATE obras SET status_comercial = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (novo_status, obra_id))
    conn.commit()
    conn.close()

def atualizar_score_obra(obra_id, novo_score, prioridade, breakdown_json):
    """Atualiza pontuação recalculada da obra."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE obras SET score = ?, prioridade = ?, score_breakdown = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (novo_score, prioridade, breakdown_json, obra_id))
    conn.commit()
    conn.close()

def adicionar_tarefa(obra_id, titulo, tipo, data_limite, prioridade="Normal", empresa_id=None, contacto_id=None):
    """Adiciona uma tarefa de seguimento."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO tarefas (obra_id, empresa_id, contacto_id, titulo, tipo, data_limite, prioridade)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (obra_id, empresa_id, contacto_id, titulo, tipo, data_limite, prioridade))
    conn.commit()
    conn.close()

def concluir_tarefa(tarefa_id, resultado):
    """Conclui uma tarefa registando o resultado comercial."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE tarefas SET estado = 'Concluída', resultado_interacao = ?, data_conclusao = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (resultado, tarefa_id))
    conn.commit()
    conn.close()

def marcar_alerta_processado(alerta_id, obra_id=None):
    """Regista que um alerta foi triado pelo utilizador."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE alertas_recolha SET processado = 1, obra_id_gerada = ?
    WHERE id = ?
    """, (obra_id, alerta_id))
    conn.commit()
    conn.close()
