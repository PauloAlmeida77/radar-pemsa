"""
database.py - Módulo de gestão da base de dados, integridade, deduplicação,
atualização de obras existentes, deteção de conflitos e histórico de sincronização.
"""

import sqlite3
import os
import sys
import re
import json
import unicodedata
from datetime import datetime, date

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Permite configurar caminho persistente via variável de ambiente RADAR_DB_PATH
DB_PATH = os.environ.get("RADAR_DB_PATH", os.path.join(CURRENT_DIR, "radar_pemsa.db"))

CODIGOS_DEMO_CONHECIDOS = {
    "PEMSA-2026-SINES",
    "PEMSA-2026-HLISBOA",
    "PEMSA-2026-FAMALICAO",
    "PEMSA-2026-CASTANHEIRA",
    "PEMSA-2026-COMPORTA",
    "PEMSA-2026-MADEIRA",
    "PEMSA-2026-MAIA",
    "PEMSA-2026-CORUCHE",
    "PEMSA-2026-SOMFY",
    "PEMSA-2026-LOGICOR",
    "PEMSA-2026-SOPHIA",
}

ESTADOS_VERIFICACAO_VALIDOS = (
    "Por verificar",
    "Confirmado por fonte",
    "Confirmado por contacto direto",
)


def get_connection(db_path=None):
    """Obtém uma conexão à base de dados SQLite."""
    caminho = db_path or os.environ.get("RADAR_DB_PATH", DB_PATH)
    conn = sqlite3.connect(caminho, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _normalizar_texto_chave(texto):
    """Remove acentos, pontuação e stopwords para construção de chave estável de deduplicação."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto).lower())
    sem_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    tokens = re.findall(r"[a-z0-9]+", sem_acentos)
    stopwords = {
        "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas", "para", "por", "com",
        "um", "uma", "novo", "nova", "novos", "novas", "obra", "obras", "construcao",
        "empreitada", "projeto", "execucao", "fase", "lote", "portugal", "concurso", "publico",
        "milhoes", "euros", "vai", "ser", "tera", "avanca", "arranca", "unidade", "grupo"
    }
    filtrados = [t for t in tokens if len(t) > 2 and t not in stopwords]
    return "-".join(filtrados[:7])


def gerar_chave_estavel_obra(titulo, concelho="", distrito="", promotor="", codigo_oficial=None):
    """
    Gera uma chave estável para deduplicação de uma obra:
    1. Usa identificador oficial quando disponível.
    2. Na sua ausência, combina localização normalizada + promotor normalizado + núcleo semântico do título.
    """
    if codigo_oficial and str(codigo_oficial).strip():
        cod_norm = re.sub(r"[^a-zA-Z0-9\-/]", "", str(codigo_oficial).strip()).upper()
        if cod_norm:
            return f"OFICIAL:{cod_norm}"

    loc_raw = concelho if (concelho and concelho != "Por verificar") else (distrito or "pt")
    loc_norm = _normalizar_texto_chave(loc_raw) or "pt"
    prom_norm = _normalizar_texto_chave(promotor)[:25] if promotor and promotor != "Por verificar" else ""
    tit_norm = _normalizar_texto_chave(titulo) or "obra"

    if prom_norm:
        return f"OBRA:{loc_norm}:{prom_norm}:{tit_norm}"
    return f"OBRA:{loc_norm}:{tit_norm}"


def _calcular_similaridade_titulos(t1, t2):
    """Calcula a sobreposição de tokens relevantes entre dois títulos de obras."""
    s1 = set(_normalizar_texto_chave(t1).split("-")) - {""}
    s2 = set(_normalizar_texto_chave(t2).split("-")) - {""}
    if not s1 or not s2:
        return 0.0
    inter = len(s1.intersection(s2))
    menor = min(len(s1), len(s2))
    return inter / float(menor) if menor > 0 else 0.0


def init_db(db_path=None):
    """Inicializa e migra de forma não-destrutiva todas as tabelas da base de dados."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Tabela de Obras
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS obras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        codigo_ref TEXT UNIQUE,
        chave_estavel TEXT,
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
        data_publicacao_fonte TEXT,
        data_consulta_fonte TIMESTAMP,
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
        estado_verificacao TEXT DEFAULT 'Por verificar',
        origem_registo TEXT DEFAULT 'REAL',
        tem_conflito INTEGER DEFAULT 0,
        editado_manualmente INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Migração não-destrutiva de colunas em obras
    cursor.execute("PRAGMA table_info(obras)")
    colunas_obras = {col[1] for col in cursor.fetchall()}
    novas_colunas_obras = [
        ("chave_estavel", "TEXT"),
        ("data_publicacao_fonte", "TEXT"),
        ("data_consulta_fonte", "TIMESTAMP"),
        ("responsavel_nome", "TEXT"),
        ("responsavel_cargo", "TEXT"),
        ("responsavel_empresa", "TEXT"),
        ("responsavel_contacto", "TEXT"),
        ("estado_verificacao", "TEXT DEFAULT 'Por verificar'"),
        ("origem_registo", "TEXT DEFAULT 'REAL'"),
        ("tem_conflito", "INTEGER DEFAULT 0"),
        ("editado_manualmente", "INTEGER DEFAULT 0"),
    ]
    for col_n, col_t in novas_colunas_obras:
        if col_n not in colunas_obras:
            cursor.execute(f"ALTER TABLE obras ADD COLUMN {col_n} {col_t}")

    # 2. Tabela de Empresas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS empresas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        nif TEXT,
        tipo TEXT NOT NULL,
        distrito TEXT,
        cidade TEXT,
        morada TEXT,
        telefone TEXT,
        email TEXT,
        website TEXT,
        nivel_relacionamento TEXT DEFAULT 'Sem Contacto',
        estado_verificacao TEXT DEFAULT 'Por verificar',
        origem_registo TEXT DEFAULT 'REAL',
        notas TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("PRAGMA table_info(empresas)")
    cols_emp = {col[1] for col in cursor.fetchall()}
    for col_n, col_t in [
        ("estado_verificacao", "TEXT DEFAULT 'Por verificar'"),
        ("origem_registo", "TEXT DEFAULT 'REAL'"),
    ]:
        if col_n not in cols_emp:
            cursor.execute(f"ALTER TABLE empresas ADD COLUMN {col_n} {col_t}")

    # 3. Tabela de Intervenientes na Obra (Obra <-> Empresa)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS obra_empresas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        obra_id INTEGER NOT NULL,
        empresa_id INTEGER NOT NULL,
        papel TEXT NOT NULL,
        confirmado INTEGER DEFAULT 0,
        estado_verificacao TEXT DEFAULT 'Por verificar',
        fonte_evidencia TEXT,
        notas TEXT,
        FOREIGN KEY (obra_id) REFERENCES obras (id) ON DELETE CASCADE,
        FOREIGN KEY (empresa_id) REFERENCES empresas (id) ON DELETE CASCADE,
        UNIQUE(obra_id, empresa_id, papel)
    )
    """)
    cursor.execute("PRAGMA table_info(obra_empresas)")
    cols_oe = {col[1] for col in cursor.fetchall()}
    for col_n, col_t in [
        ("estado_verificacao", "TEXT DEFAULT 'Por verificar'"),
        ("fonte_evidencia", "TEXT"),
    ]:
        if col_n not in cols_oe:
            cursor.execute(f"ALTER TABLE obra_empresas ADD COLUMN {col_n} {col_t}")

    # 4. Tabela de Contactos
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
        estado_verificacao TEXT DEFAULT 'Por verificar',
        origem_registo TEXT DEFAULT 'REAL',
        notas TEXT,
        FOREIGN KEY (empresa_id) REFERENCES empresas (id) ON DELETE CASCADE
    )
    """)
    cursor.execute("PRAGMA table_info(contactos)")
    cols_ct = {col[1] for col in cursor.fetchall()}
    for col_n, col_t in [
        ("estado_verificacao", "TEXT DEFAULT 'Por verificar'"),
        ("origem_registo", "TEXT DEFAULT 'REAL'"),
    ]:
        if col_n not in cols_ct:
            cursor.execute(f"ALTER TABLE contactos ADD COLUMN {col_n} {col_t}")

    # 5. Tabela de Produtos PÉMSA na Obra
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS obra_produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        obra_id INTEGER NOT NULL,
        familia_produto TEXT NOT NULL,
        nivel_potencial TEXT DEFAULT 'Potencial Teórico',
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
        tipo TEXT NOT NULL,
        data_limite DATE NOT NULL,
        prioridade TEXT DEFAULT 'Normal',
        estado TEXT DEFAULT 'Pendente',
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
        data_consulta TIMESTAMP,
        entidade_promotora TEXT,
        resumo_bruto TEXT,
        segmento_estimado TEXT,
        regiao_estimada TEXT,
        motivo_validacao TEXT,
        origem_registo TEXT DEFAULT 'REAL',
        processado INTEGER DEFAULT 0,
        obra_id_gerada INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("PRAGMA table_info(alertas_recolha)")
    cols_al = {col[1] for col in cursor.fetchall()}
    for col_n, col_t in [
        ("data_consulta", "TIMESTAMP"),
        ("motivo_validacao", "TEXT"),
        ("origem_registo", "TEXT DEFAULT 'REAL'"),
    ]:
        if col_n not in cols_al:
            cursor.execute(f"ALTER TABLE alertas_recolha ADD COLUMN {col_n} {col_t}")

    # 8. Tabela de Histórico de Alterações e Conflitos por Obra
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS obra_historico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        obra_id INTEGER NOT NULL,
        acao TEXT NOT NULL, -- ATUALIZACAO, CONFLITO, AUDITORIA_DEMO, REVISAO_MANUAL
        campo TEXT NOT NULL,
        valor_anterior TEXT,
        valor_novo TEXT,
        fonte_nome TEXT,
        fonte_url TEXT,
        data_publicacao_fonte TEXT,
        resolvido INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (obra_id) REFERENCES obras (id) ON DELETE CASCADE
    )
    """)

    # 9. Tabela de Registo de Sincronizações (Auditoria de Execuções)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sincronizacoes_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inicio_ts TIMESTAMP NOT NULL,
        fim_ts TIMESTAMP NOT NULL,
        modo TEXT NOT NULL,
        estado_global TEXT NOT NULL, -- Sucesso, Sucesso parcial, Falha
        fontes_consultadas INTEGER DEFAULT 0,
        fontes_sucesso INTEGER DEFAULT 0,
        fontes_erro INTEGER DEFAULT 0,
        noticias_encontradas INTEGER DEFAULT 0,
        obras_criadas INTEGER DEFAULT 0,
        obras_atualizadas INTEGER DEFAULT 0,
        duplicados_ignorados INTEGER DEFAULT 0,
        alertas_pendentes INTEGER DEFAULT 0,
        detalhes_json TEXT
    )
    """)

    # 10. Tabela de Configurações
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracoes (
        chave TEXT PRIMARY KEY,
        valor TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

    # Executar auditoria e marcação não-destrutiva dos dados de demonstração existentes
    auditar_e_separar_dados_demonstracao(db_path=db_path)


def auditar_e_separar_dados_demonstracao(db_path=None):
    """
    Identifica os dados de demonstração já existentes na base de dados e separa-os das
    oportunidades reais (origem_registo='DEMO', estado_verificacao='Por verificar'),
    sem apagar obras, tarefas, notas comerciais ou histórico.
    Regista no histórico os campos suspeitos que carecem de verificação documental.
    """
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute("SELECT * FROM obras")
    todas_obras = [dict(r) for r in cur.fetchall()]

    for ob in todas_obras:
        oid = ob["id"]
        cod = ob.get("codigo_ref") or ""
        f_url = (ob.get("fonte_url") or "").strip()

        # Garantir que todas as obras têm chave_estavel preenchida
        if not ob.get("chave_estavel"):
            chave = gerar_chave_estavel_obra(
                ob.get("titulo", ""),
                ob.get("concelho", ""),
                ob.get("distrito", ""),
                "",
                codigo_oficial=None
            )
            cur.execute("UPDATE obras SET chave_estavel = ? WHERE id = ?", (chave, oid))

        # Identificar se é um registo proveniente de seed_data / lote demonstrativo
        urls_genericos_demo = {
            "https://eco.sapo.pt/",
            "https://jornaleconomico.sapo.pt/",
            "https://diarioimobiliario.pt/",
            "https://participa.pt/",
            "https://startcampus.pt/press/fase2-sines40",
            "https://eco.sapo.pt/2026/fabrica-famalicao",
            "https://construir.pt/panattoni-castanheira",
            "https://cm-grandola.pt/licenciamento-muda",
            "https://joram.madeira.gov.pt/hospital-central",
            "https://construcaomagazine.pt/maia-frio-logistica",
        }

        is_demo = (cod in CODIGOS_DEMO_CONHECIDOS) or (f_url in urls_genericos_demo)
        if is_demo and ob.get("editado_manualmente", 0) == 0:
            cur.execute("""
                UPDATE obras
                SET origem_registo = 'DEMO',
                    estado_verificacao = CASE
                        WHEN estado_verificacao IS NULL OR estado_verificacao = '' THEN 'Por verificar'
                        ELSE estado_verificacao
                    END
                WHERE id = ?
            """, (oid,))

            # Registar aviso de auditoria apenas uma vez por obra
            cur.execute(
                "SELECT COUNT(*) FROM obra_historico WHERE obra_id = ? AND acao = 'AUDITORIA_DEMO'",
                (oid,)
            )
            if cur.fetchone()[0] == 0:
                motivo_suspeita = (
                    f"Registo de demonstração ({cod}): intervenientes ({ob.get('responsavel_empresa')}), "
                    f"contactos e URL ({f_url}) foram pré-populados sem link específico verificável. "
                    f"Marcado como DEMO / 'Por verificar' para não induzir em erro comercial."
                )
                cur.execute("""
                    INSERT INTO obra_historico (obra_id, acao, campo, valor_anterior, valor_novo, fonte_nome, fonte_url)
                    VALUES (?, 'AUDITORIA_DEMO', 'Integridade do Registo', ?, 'Marcado como DEMO (Por verificar)', ?, ?)
                """, (oid, motivo_suspeita, ob.get("fonte_nome"), f_url))

    # Marcar contactos sem confirmação direta como 'Por verificar' e origem 'DEMO' se vieram do seed
    cur.execute("""
        UPDATE contactos
        SET estado_verificacao = 'Por verificar',
            origem_registo = 'DEMO'
        WHERE estado_verificacao IS NULL OR estado_verificacao = ''
    """)

    # Marcar alertas exemplificativos com links genéricos como DEMO
    cur.execute("""
        UPDATE alertas_recolha
        SET origem_registo = 'DEMO',
            motivo_validacao = 'Alerta de demonstração inicial (URL genérico sem artigo específico)'
        WHERE link IN ('https://eco.sapo.pt/', 'https://jornaleconomico.sapo.pt/', 'https://participa.pt/', 'https://ted.europa.eu/en/notice/-/detail/2026-PT-LABS')
    """)

    conn.commit()
    conn.close()


def listar_registos_suspeitos(db_path=None):
    """
    Devolve o relatório de todos os registos de demonstração ou com conflitos/dados suspeitos
    para revisão pelo utilizador antes de qualquer limpeza.
    """
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT o.id, o.codigo_ref, o.titulo, o.distrito, o.concelho, o.fase,
               o.valor_estimado, o.fonte_nome, o.fonte_url,
               o.responsavel_nome, o.responsavel_empresa, o.responsavel_contacto,
               o.origem_registo, o.estado_verificacao, o.tem_conflito, o.notas_comerciais
        FROM obras o
        WHERE o.origem_registo = 'DEMO'
           OR o.estado_verificacao = 'Por verificar'
           OR o.tem_conflito = 1
        ORDER BY o.tem_conflito DESC, o.origem_registo ASC, o.id ASC
    """)
    rows = [dict(r) for r in cur.fetchall()]

    for r in rows:
        cur.execute("""
            SELECT id, acao, campo, valor_anterior, valor_novo, fonte_nome, fonte_url, resolvido, created_at
            FROM obra_historico
            WHERE obra_id = ?
            ORDER BY created_at DESC
        """, (r["id"],))
        r["historico"] = [dict(h) for h in cur.fetchall()]

    conn.close()
    return rows


def limpar_atribuicoes_nao_verificadas_obra(obra_id, db_path=None):
    """
    Limpa atribuições suspeitas/não verificadas de empresas e contactos numa obra (colocando 'Por verificar'),
    preservando 100% das tarefas, notas comerciais, estado do pipeline e histórico.
    """
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM obras WHERE id = ?", (obra_id,))
    ob = cur.fetchone()
    if not ob:
        conn.close()
        return False

    ob_dict = dict(ob)
    cur.execute("""
        INSERT INTO obra_historico (obra_id, acao, campo, valor_anterior, valor_novo, fonte_nome, fonte_url)
        VALUES (?, 'REVISAO_MANUAL', 'responsavel_empresa / responsavel_contacto', ?, 'Por verificar (Atribuições de demonstração limpas)', 'Revisão de Integridade', '')
    """, (obra_id, f"{ob_dict.get('responsavel_empresa')} | {ob_dict.get('responsavel_contacto')}"))

    cur.execute("""
        UPDATE obras
        SET responsavel_nome = 'Por verificar',
            responsavel_cargo = 'Por verificar',
            responsavel_empresa = 'Por verificar',
            responsavel_contacto = 'Por verificar',
            estado_verificacao = 'Por verificar',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (obra_id,))

    # Marcar relações obra_empresas como não confirmadas (sem apagar)
    cur.execute("""
        UPDATE obra_empresas
        SET confirmado = 0, estado_verificacao = 'Por verificar'
        WHERE obra_id = ?
    """, (obra_id,))

    conn.commit()
    conn.close()
    return True


def obter_config(chave, default=None, db_path=None):
    """Obtém uma chave de configuração."""
    conn = get_connection(db_path)
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


def definir_config(chave, valor, db_path=None):
    """Define ou atualiza uma chave de configuração."""
    conn = get_connection(db_path)
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


# =====================================================================
# DEDUPLICAÇÃO, ATUALIZAÇÃO SELETIVA E DETEÇÃO DE CONFLITOS
# =====================================================================

def encontrar_obra_existente(cur, dados_analisados):
    """
    Procura uma obra já existente na base de dados utilizando:
    1. Chave estável exata (identificador oficial ou chave normalizada).
    2. URL da fonte idêntico (quando não genérico).
    3. Correspondência de localização (concelho/distrito) + segmento + elevada similaridade de título (>= 0.60).
    """
    promotor_nome = ""
    for e in dados_analisados.get("empresas_sugeridas", []):
        if e.get("papel") == "Promotor/Dono":
            promotor_nome = e.get("nome", "")
            break

    chave_cand = gerar_chave_estavel_obra(
        dados_analisados.get("titulo", ""),
        dados_analisados.get("concelho", ""),
        dados_analisados.get("distrito", ""),
        promotor_nome,
        codigo_oficial=dados_analisados.get("codigo_oficial")
    )

    # 1. Por chave estável
    cur.execute("SELECT * FROM obras WHERE chave_estavel = ?", (chave_cand,))
    row = cur.fetchone()
    if row:
        return dict(row), chave_cand

    # 2. Por URL específico ou título exato
    f_url = (dados_analisados.get("fonte_url") or "").strip()
    if f_url and len(f_url) > 28:
        cur.execute("SELECT * FROM obras WHERE fonte_url = ?", (f_url,))
        row = cur.fetchone()
        if row:
            return dict(row), chave_cand

    cur.execute("SELECT * FROM obras WHERE LOWER(titulo) = LOWER(?)", (dados_analisados.get("titulo", ""),))
    row = cur.fetchone()
    if row:
        return dict(row), chave_cand

    # 3. Por sobreposição semântica na mesma localização e segmento
    dist = dados_analisados.get("distrito", "")
    conc = dados_analisados.get("concelho", "")
    seg = dados_analisados.get("segmento", "")
    val_novo = (dados_analisados.get("valor_estimado") or "").split("(")[0].strip()

    cur.execute("SELECT * FROM obras WHERE distrito = ? OR concelho = ?", (dist, conc))
    candidatas = [dict(r) for r in cur.fetchall()]
    for cand in candidatas:
        sim = _calcular_similaridade_titulos(dados_analisados.get("titulo", ""), cand.get("titulo", ""))
        mesmo_concelho = bool(conc and conc != "Por verificar" and cand.get("concelho") == conc)
        mesmo_segmento = (cand.get("segmento") == seg)
        if sim >= 0.60:
            return cand, cand.get("chave_estavel") or chave_cand
        if mesmo_concelho and mesmo_segmento and sim >= 0.40:
            return cand, cand.get("chave_estavel") or chave_cand
        if mesmo_concelho and mesmo_segmento and val_novo and val_novo != "Por verificar":
            # Comparar número principal do valor estimado (ex: 220 ou 10)
            num_n = re.findall(r"\d+", val_novo)
            num_c = re.findall(r"\d+", cand.get("valor_estimado") or "")
            if num_n and num_c and num_n[0] == num_c[0]:
                return cand, cand.get("chave_estavel") or chave_cand

    return None, chave_cand


def _valores_equivalentes(campo, val_a, val_b):
    """Compara dois valores de campo ignorando diferenças cosméticas de formatação (ex: '220.000.000 €' vs '220 M€')."""
    a = (val_a or "").strip().lower()
    b = (val_b or "").strip().lower()
    if a == b:
        return True
    if campo == "valor_estimado":
        def _extrair_milhoes(s):
            s_clean = s.replace(".", "").replace(",", ".")
            m_milhoes = re.search(r"(\d+(?:\.\d+)?)\s*(?:m€|milh)", s_clean)
            if m_milhoes:
                return float(m_milhoes.group(1))
            m_num = re.search(r"(\d+)", s_clean)
            if m_num:
                v = float(m_num.group(1))
                if v >= 1_000_000:
                    return v / 1_000_000.0
                return v
            return None
        va, vb = _extrair_milhoes(a), _extrair_milhoes(b)
        if va is not None and vb is not None and abs(va - vb) < 0.05:
            return True
    return False


def processar_obra_sincronizada(cur, dados_analisados, mapa_empresas):
    """
    Insere uma nova obra (se ainda não existir) ou atualiza uma obra existente apenas nos
    campos sustentados por novas evidências:
    - Preserva contactos confirmados, notas comerciais, tarefas, estado do pipeline e edições manuais.
    - Regista histórico de todas as alterações em `obra_historico`.
    - Se a nova fonte divergir de um valor já confirmado, assinala conflito (`tem_conflito = 1`)
      em vez de substituir silenciosamente.
    Retorna: ('CRIADA' | 'ATUALIZADA' | 'DUPLICADO', obra_id)
    """
    obra_existente, chave_estavel = encontrar_obra_existente(cur, dados_analisados)
    fonte_nome = dados_analisados.get("fonte_nome") or "Fonte Pública"
    fonte_url = dados_analisados.get("fonte_url") or ""
    data_pub = dados_analisados.get("data_publicacao")
    data_cons = dados_analisados.get("data_consulta") or datetime.now().isoformat(timespec="seconds")

    if not obra_existente:
        # Criar nova obra verificável
        cod_ref = dados_analisados.get("codigo_oficial") or f"PEMSA-REAL-{int(datetime.now().timestamp())}-{abs(hash(chave_estavel)) % 10000:04d}"
        cur.execute("""
            INSERT INTO obras (
                titulo, codigo_ref, chave_estavel, segmento, regiao, distrito, concelho,
                morada_localizacao, lat, lon, fase, status_comercial, score, score_breakdown,
                prioridade, valor_estimado, prazo_previsto, data_detecao,
                data_publicacao_fonte, data_consulta_fonte, fonte_tipo, fonte_nome, fonte_url,
                resumo, timing_fornecimento, proxima_acao, notas_comerciais,
                responsavel_nome, responsavel_cargo, responsavel_empresa, responsavel_contacto,
                estado_verificacao, origem_registo, tem_conflito, editado_manualmente
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'REAL', 0, 0)
        """, (
            dados_analisados["titulo"],
            cod_ref,
            chave_estavel,
            dados_analisados["segmento"],
            dados_analisados["regiao"],
            dados_analisados["distrito"],
            dados_analisados["concelho"],
            f"{dados_analisados['concelho']}, {dados_analisados['distrito']}",
            None,
            None,
            dados_analisados["fase"],
            "Nova Oportunidade",
            dados_analisados["score"],
            json.dumps(dados_analisados["score_breakdown"], ensure_ascii=False),
            dados_analisados["prioridade"],
            dados_analisados.get("valor_estimado") or "Por verificar",
            "Por verificar",
            data_pub or date.today().isoformat(),
            data_pub,
            data_cons,
            dados_analisados.get("fonte_tipo") or "Fonte Pública",
            fonte_nome,
            fonte_url,
            dados_analisados["resumo"],
            dados_analisados["timing_fornecimento"],
            dados_analisados["proxima_acao"],
            None,  # Nunca inventa notas comerciais
            dados_analisados["responsavel_nome"],
            dados_analisados["responsavel_cargo"],
            dados_analisados["responsavel_empresa"],
            dados_analisados["responsavel_contacto"],
            dados_analisados.get("estado_verificacao") or "Por verificar",
        ))
        nova_id = cur.lastrowid

        # Registar criação no histórico
        cur.execute("""
            INSERT INTO obra_historico (obra_id, acao, campo, valor_anterior, valor_novo, fonte_nome, fonte_url, data_publicacao_fonte)
            VALUES (?, 'CRIACAO', 'Obra Criada', NULL, ?, ?, ?, ?)
        """, (nova_id, dados_analisados["titulo"], fonte_nome, fonte_url, data_pub))

        # Associar produtos sugeridos
        for prod in dados_analisados.get("produtos_sugeridos", []):
            cur.execute("""
                INSERT INTO obra_produtos (obra_id, familia_produto, nivel_potencial, especificacao_detalhe)
                VALUES (?, ?, ?, ?)
            """, (nova_id, prod["familia_produto"], prod.get("nivel_potencial", "Potencial Teórico"), prod.get("especificacao_detalhe", "")))

        # Associar empresas confirmadas na fonte
        _associar_empresas_extraidas(cur, nova_id, dados_analisados.get("empresas_sugeridas", []), mapa_empresas, fonte_nome, fonte_url)

        return "CRIADA", nova_id

    # Obra já existe: verificar se há nova evidência ou conflito
    oid = obra_existente["id"]

    # Se o mesmo URL já foi registado na obra ou no histórico e não traz campos novos, é duplicado
    if fonte_url and obra_existente.get("fonte_url") == fonte_url:
        # Mesmo URL: verificar se algum campo em 'Por verificar' pode ser preenchido
        pass

    campos_atualizados = 0
    conflitos_detetados = 0
    protegido_manual = bool(obra_existente.get("editado_manualmente", 0)) or (
        obra_existente.get("estado_verificacao") == "Confirmado por contacto direto"
    )
    is_demo_existente = obra_existente.get("origem_registo") == "DEMO"

    # Lista de campos passíveis de enriquecimento por novas fontes
    regras_campos = [
        ("fase", dados_analisados.get("fase")),
        ("valor_estimado", dados_analisados.get("valor_estimado")),
        ("responsavel_empresa", dados_analisados.get("responsavel_empresa")),
        ("concelho", dados_analisados.get("concelho")),
        ("distrito", dados_analisados.get("distrito")),
    ]

    for campo, novo_val in regras_campos:
        if not novo_val or str(novo_val).startswith("Por verificar"):
            continue

        val_atual = (obra_existente.get(campo) or "").strip()
        vazio_ou_por_verificar = (
            not val_atual
            or val_atual.startswith("Por verificar")
            or val_atual in ("Sob Consulta", "Sob Avaliação", "Empresa N/D", "Cargo N/D")
        )

        if vazio_ou_por_verificar:
            cur.execute(f"UPDATE obras SET {campo} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (novo_val, oid))
            cur.execute("""
                INSERT INTO obra_historico (obra_id, acao, campo, valor_anterior, valor_novo, fonte_nome, fonte_url, data_publicacao_fonte)
                VALUES (?, 'ATUALIZACAO', ?, ?, ?, ?, ?, ?)
            """, (oid, campo, val_atual or "Por verificar", novo_val, fonte_nome, fonte_url, data_pub))
            campos_atualizados += 1
        elif not _valores_equivalentes(campo, val_atual, str(novo_val)):
            # Se o registo anterior era DEMO e ainda não editado manualmente, ou se é um conflito entre fontes
            if not protegido_manual:
                # Assinalar conflito sem sobrescrever silenciosamente!
                cur.execute("""
                    SELECT COUNT(*) FROM obra_historico
                    WHERE obra_id = ? AND acao = 'CONFLITO' AND campo = ? AND valor_novo = ?
                """, (oid, campo, novo_val))
                if cur.fetchone()[0] == 0:
                    cur.execute("UPDATE obras SET tem_conflito = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (oid,))
                    cur.execute("""
                        INSERT INTO obra_historico (obra_id, acao, campo, valor_anterior, valor_novo, fonte_nome, fonte_url, data_publicacao_fonte)
                        VALUES (?, 'CONFLITO', ?, ?, ?, ?, ?, ?)
                    """, (oid, campo, val_atual, novo_val, fonte_nome, fonte_url, data_pub))
                    conflitos_detetados += 1

    # Atualizar URL específico e data de publicação real se a obra existente tinha apenas um URL genérico de DEMO
    url_atual = (obra_existente.get("fonte_url") or "").strip()
    if fonte_url and len(fonte_url) > 28 and (not url_atual or len(url_atual) <= 28 or is_demo_existente):
        if url_atual != fonte_url:
            novo_estado_verif = dados_analisados.get("estado_verificacao") or "Por verificar"
            # Se o registo era DEMO e a fonte real não confirma as empresas que estavam no DEMO,
            # limpar atribuições de exemplo não verificadas para 'Por verificar'
            if is_demo_existente and not protegido_manual and novo_estado_verif == "Por verificar":
                emp_antiga = obra_existente.get("responsavel_empresa") or "Por verificar"
                cur.execute("""
                    UPDATE obras
                    SET responsavel_nome = 'Por verificar',
                        responsavel_cargo = 'Por verificar',
                        responsavel_empresa = 'Por verificar',
                        responsavel_contacto = 'Por verificar',
                        estado_verificacao = 'Por verificar'
                    WHERE id = ?
                """, (oid,))
                if emp_antiga != "Por verificar":
                    cur.execute("""
                        INSERT INTO obra_historico (obra_id, acao, campo, valor_anterior, valor_novo, fonte_nome, fonte_url, data_publicacao_fonte)
                        VALUES (?, 'SANEAMENTO_DEMO', 'responsavel_empresa', ?, 'Por verificar', ?, ?, ?)
                    """, (oid, emp_antiga, fonte_nome, fonte_url, data_pub))

            cur.execute("""
                UPDATE obras
                SET fonte_url = ?, fonte_nome = ?, data_publicacao_fonte = COALESCE(?, data_publicacao_fonte),
                    data_consulta_fonte = ?, origem_registo = 'REAL',
                    estado_verificacao = CASE
                        WHEN ? = 'Confirmado por fonte' AND estado_verificacao = 'Por verificar' THEN 'Confirmado por fonte'
                        ELSE estado_verificacao
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (fonte_url, fonte_nome, data_pub, data_cons, novo_estado_verif, oid))
            cur.execute("""
                INSERT INTO obra_historico (obra_id, acao, campo, valor_anterior, valor_novo, fonte_nome, fonte_url, data_publicacao_fonte)
                VALUES (?, 'ATUALIZACAO', 'fonte_url', ?, ?, ?, ?, ?)
            """, (oid, url_atual, fonte_url, fonte_nome, fonte_url, data_pub))
            campos_atualizados += 1

    # Associar novas empresas confirmadas pela fonte
    novas_emp_assoc = _associar_empresas_extraidas(cur, oid, dados_analisados.get("empresas_sugeridas", []), mapa_empresas, fonte_nome, fonte_url)
    campos_atualizados += novas_emp_assoc

    if campos_atualizados > 0 or conflitos_detetados > 0:
        cur.execute("UPDATE obras SET data_consulta_fonte = ? WHERE id = ?", (data_cons, oid))
        return "ATUALIZADA", oid

    return "DUPLICADO", oid


def _associar_empresas_extraidas(cur, obra_id, empresas_sugeridas, mapa_empresas, fonte_nome, fonte_url):
    """Cria/associa empresas confirmadas pela fonte à obra, registando a fonte da evidência."""
    adicionadas = 0
    for emp in empresas_sugeridas:
        nome_e = emp["nome"]
        papel_e = emp["papel"]
        tipo_e = emp.get("tipo", "Promotor")
        emp_id = mapa_empresas.get(nome_e.lower())
        if not emp_id:
            cur.execute("""
                INSERT INTO empresas (nome, tipo, distrito, cidade, telefone, email, nivel_relacionamento, estado_verificacao, origem_registo, notas)
                VALUES (?, ?, 'Por verificar', 'Por verificar', 'Por verificar', 'Por verificar', 'Sem Contacto', 'Confirmado por fonte', 'REAL', ?)
            """, (nome_e, tipo_e, f"Identificada na fonte: {fonte_nome}"))
            emp_id = cur.lastrowid
            mapa_empresas[nome_e.lower()] = emp_id

        cur.execute("SELECT id FROM obra_empresas WHERE obra_id = ? AND empresa_id = ? AND papel = ?", (obra_id, emp_id, papel_e))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO obra_empresas (obra_id, empresa_id, papel, confirmado, estado_verificacao, fonte_evidencia, notas)
                VALUES (?, ?, ?, 1, 'Confirmado por fonte', ?, ?)
            """, (obra_id, emp_id, papel_e, fonte_url or fonte_nome, f"Confirmado por {fonte_nome}"))
            adicionadas += 1
    return adicionadas


# =====================================================================
# MOTOR DE SINCRONIZAÇÃO REAL (MANUAL E AGENDADO)
# =====================================================================

def executar_sincronizacao_radar(forcar=True, modo="MANUAL", fontes=None, timeout=8, session=None, db_path=None):
    """
    Executa a sincronização real do Radar PÉMSA:
    - Não usa dados fictícios nem bloqueia por semana ISO quando `forcar=True`.
    - Consulta todos os conectores reais configurados.
    - Cria novas obras quando há evidência verificável suficiente.
    - Atualiza obras existentes quando há novas evidências ou assinala conflitos.
    - Guarda notícias sem evidência suficiente como alertas pendentes de validação.
    - Regista e devolve um relatório completo (início, fim, fontes, sucessos, erros, contagens).
    """
    from scrapers import recolher_todas_as_fontes, avaliar_evidencia_item, analisar_texto_obra

    init_db(db_path=db_path)
    inicio_dt = datetime.now()
    inicio_ts = inicio_dt.isoformat(timespec="seconds")

    # Se não for forçado (ex.: abertura passiva da app), verifica se já sincronizou nas últimas 12 horas
    if not forcar:
        ult_sync_ts = obter_config("ultima_sincronizacao_ts", db_path=db_path)
        if ult_sync_ts:
            try:
                dt_ult = datetime.fromisoformat(ult_sync_ts)
                horas = (inicio_dt - dt_ult).total_seconds() / 3600.0
                if horas < 12.0:
                    return {
                        "executado": False,
                        "motivo_ignorado": f"Sincronização automática já realizada há {horas:.1f}h ({ult_sync_ts}). Use 'Atualizar Agora' para forçar.",
                        "estado_global": obter_config("ultimo_estado_sync", "Sucesso", db_path=db_path),
                        "inicio_ts": inicio_ts,
                        "fim_ts": inicio_ts,
                        "fontes_consultadas": 0,
                        "fontes_sucesso": 0,
                        "fontes_erro": 0,
                        "noticias_encontradas": 0,
                        "obras_criadas": 0,
                        "obras_atualizadas": 0,
                        "duplicados_ignorados": 0,
                        "alertas_pendentes": 0,
                        "relatorios_fontes": [],
                        "erros": []
                    }
            except Exception:
                pass

    res_recolha = recolher_todas_as_fontes(fontes=fontes, timeout=timeout, session=session)
    estado_global = res_recolha["estado_global"]
    itens_recolhidos = res_recolha["itens_recolhidos"]

    obras_criadas = 0
    obras_atualizadas = 0
    duplicados_ignorados = 0
    alertas_pendentes = 0

    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute("SELECT id, nome FROM empresas")
    mapa_empresas = {r["nome"].lower(): r["id"] for r in cur.fetchall()}

    urls_vistos_ciclo = set()

    for item in itens_recolhidos:
        titulo_it = item.get("titulo") or ""
        link_it = item.get("link") or ""
        resumo_it = item.get("resumo_bruto") or ""
        fonte_nome_it = item.get("fonte_nome") or "Fonte Pública"
        fonte_tipo_it = item.get("fonte_tipo") or "Imprensa"
        data_pub_it = item.get("data_publicacao")
        data_cons_it = item.get("data_consulta") or inicio_ts

        chave_ciclo = (link_it.strip() or titulo_it.strip().lower())
        if chave_ciclo in urls_vistos_ciclo:
            duplicados_ignorados += 1
            continue
        urls_vistos_ciclo.add(chave_ciclo)

        evid = avaliar_evidencia_item(titulo_it, resumo_it, fonte_tipo=fonte_tipo_it)
        if not evid["relevante_radar"]:
            continue

        if evid["evidencia_suficiente_obra"]:
            dados_obra = analisar_texto_obra(
                f"{titulo_it}. {resumo_it}",
                fonte_nome=fonte_nome_it,
                fonte_url=link_it,
                data_publicacao=data_pub_it
            )
            dados_obra["fonte_tipo"] = fonte_tipo_it
            dados_obra["data_consulta"] = data_cons_it

            acao_res, _ = processar_obra_sincronizada(cur, dados_obra, mapa_empresas)
            if acao_res == "CRIADA":
                obras_criadas += 1
            elif acao_res == "ATUALIZADA":
                obras_atualizadas += 1
            else:
                duplicados_ignorados += 1
        else:
            # Registar como alerta pendente de validação (se ainda não existir com o mesmo título ou link)
            cur.execute(
                "SELECT id FROM alertas_recolha WHERE LOWER(titulo) = LOWER(?) OR (link IS NOT NULL AND link != '' AND link = ?)",
                (titulo_it, link_it)
            )
            if cur.fetchone():
                duplicados_ignorados += 1
            else:
                 dados_parciais = analisar_texto_obra(
                    f"{titulo_it}. {resumo_it}",
                    fonte_nome=fonte_nome_it,
                    fonte_url=link_it,
                    data_publicacao=data_pub_it
                 )
                 promotores = [e["nome"] for e in dados_parciais.get("empresas_sugeridas", []) if e["papel"] == "Promotor/Dono"]
                 entidade_str = promotores[0] if promotores else "Por verificar"
                 cur.execute("""
                    INSERT INTO alertas_recolha (
                        fonte_tipo, fonte_nome, titulo, link, data_publicacao, data_consulta,
                        entidade_promotora, resumo_bruto, segmento_estimado, regiao_estimada,
                        motivo_validacao, origem_registo, processado
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'REAL', 0)
                 """, (
                    fonte_tipo_it,
                    fonte_nome_it,
                    titulo_it,
                    link_it,
                    data_pub_it,
                    data_cons_it,
                    entidade_str,
                    resumo_it,
                    dados_parciais["segmento"],
                    dados_parciais["regiao"],
                    evid["motivo"]
                 ))
                 alertas_pendentes += 1

    fim_dt = datetime.now()
    fim_ts = fim_dt.isoformat(timespec="seconds")
    erros_lista = [r["erro"] for r in res_recolha["relatorios_fontes"] if not r["sucesso"] and r.get("erro")]

    relatorio = {
        "executado": True,
        "modo": modo,
        "estado_global": estado_global,
        "inicio_ts": inicio_ts,
        "fim_ts": fim_ts,
        "fontes_consultadas": res_recolha["fontes_consultadas"],
        "fontes_sucesso": res_recolha["fontes_sucesso"],
        "fontes_erro": res_recolha["fontes_erro"],
        "noticias_encontradas": len(itens_recolhidos),
        "obras_criadas": obras_criadas,
        "obras_atualizadas": obras_atualizadas,
        "duplicados_ignorados": duplicados_ignorados,
        "alertas_pendentes": alertas_pendentes,
        "relatorios_fontes": res_recolha["relatorios_fontes"],
        "erros": erros_lista
    }

    cur.execute("""
        INSERT INTO sincronizacoes_log (
            inicio_ts, fim_ts, modo, estado_global,
            fontes_consultadas, fontes_sucesso, fontes_erro,
            noticias_encontradas, obras_criadas, obras_atualizadas,
            duplicados_ignorados, alertas_pendentes, detalhes_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        inicio_ts, fim_ts, modo, estado_global,
        relatorio["fontes_consultadas"], relatorio["fontes_sucesso"], relatorio["fontes_erro"],
        relatorio["noticias_encontradas"], obras_criadas, obras_atualizadas,
        duplicados_ignorados, alertas_pendentes, json.dumps(relatorio, ensure_ascii=False)
    ))

    conn.commit()
    conn.close()

    # Só atualiza o marcador de última sincronização bem-sucedida se não tiver sido Falha total
    if estado_global in ("Sucesso", "Sucesso parcial"):
        definir_config("ultima_sincronizacao", fim_dt.date().isoformat(), db_path=db_path)
        definir_config("ultima_sincronizacao_ts", fim_ts, db_path=db_path)
    definir_config("ultimo_estado_sync", estado_global, db_path=db_path)
    definir_config("ultimo_relatorio_sync", json.dumps(relatorio, ensure_ascii=False), db_path=db_path)

    return relatorio


def verificar_e_executar_sincronizacao_automatica(forcar=False, db_path=None):
    """
    Mantém compatibilidade com a assinatura `(ok, qtd)` ou devolve o relatório através
    de `executar_sincronizacao_radar`. Não está limitada à semana ISO.
    """
    modo = "MANUAL" if forcar else "AUTO"
    rel = executar_sincronizacao_radar(forcar=forcar, modo=modo, db_path=db_path)
    sucesso_bool = rel["estado_global"] in ("Sucesso", "Sucesso parcial") and rel.get("executado", False)
    total_mov = rel["obras_criadas"] + rel["obras_atualizadas"] + rel["alertas_pendentes"]
    return sucesso_bool, total_mov


def obter_ultimo_relatorio_sincronizacao(db_path=None):
    """Obtém o último relatório detalhado de sincronização guardado na BD."""
    raw = obter_config("ultimo_relatorio_sync", db_path=db_path)
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT detalhes_json FROM sincronizacoes_log ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if row and row["detalhes_json"]:
        try:
            return json.loads(row["detalhes_json"])
        except Exception:
            pass
    return None


# =====================================================================
# OPERAÇÕES DE CONSULTA (READ) E ESCRITA (WRITE)
# =====================================================================

def listar_obras(segmento=None, regiao=None, fase=None, prioridade=None, status_comercial=None, busca=None, incluir_demo=True, db_path=None):
    """Retorna uma lista de obras com filtros opcionais e filtro de separação DEMO vs REAL."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    query = "SELECT * FROM obras WHERE 1=1"
    params = []

    if not incluir_demo:
        query += " AND (origem_registo IS NULL OR origem_registo != 'DEMO')"
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

    query += " ORDER BY CASE WHEN origem_registo = 'REAL' THEN 0 ELSE 1 END, score DESC, created_at DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def obter_obra_por_id(obra_id, db_path=None):
    """Obtém os detalhes completos de uma obra, incluindo empresas, produtos, tarefas e histórico."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM obras WHERE id = ?", (obra_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    obra = dict(row)

    cursor.execute("""
        SELECT e.*, oe.papel, oe.confirmado, oe.estado_verificacao as rel_verificacao,
               oe.fonte_evidencia, oe.notas as rel_notas
        FROM empresas e
        JOIN obra_empresas oe ON e.id = oe.empresa_id
        WHERE oe.obra_id = ?
        ORDER BY oe.papel ASC
    """, (obra_id,))
    obra['empresas'] = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM obra_produtos WHERE obra_id = ?", (obra_id,))
    obra['produtos'] = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT t.*, e.nome as empresa_nome, c.nome as contacto_nome
        FROM tarefas t
        LEFT JOIN empresas e ON t.empresa_id = e.id
        LEFT JOIN contactos c ON t.contacto_id = c.id
        WHERE t.obra_id = ?
        ORDER BY t.data_limite ASC
    """, (obra_id,))
    obra['tarefas'] = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT * FROM obra_historico
        WHERE obra_id = ?
        ORDER BY created_at DESC, id DESC
    """, (obra_id,))
    obra['historico'] = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return obra


def listar_empresas(tipo=None, busca=None, db_path=None):
    """Lista empresas cadastradas com filtros."""
    conn = get_connection(db_path)
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
            SELECT o.id, o.titulo, oe.papel, oe.estado_verificacao
            FROM obras o
            JOIN obra_empresas oe ON o.id = oe.obra_id
            WHERE oe.empresa_id = ?
        """, (row['id'],))
        row['obras_participa'] = [dict(o) for o in cursor.fetchall()]

    conn.close()
    return rows


def listar_tarefas(apenas_pendentes=True, db_path=None):
    """Lista tarefas comerciais com informação da obra e contacto."""
    conn = get_connection(db_path)
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


def listar_alertas(apenas_nao_processados=False, incluir_demo=False, db_path=None):
    """Lista itens de recolha/alertas detetados."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    query = "SELECT * FROM alertas_recolha WHERE 1=1"
    if apenas_nao_processados:
        query += " AND processado = 0"
    if not incluir_demo:
        query += " AND (origem_registo IS NULL OR origem_registo != 'DEMO')"
    query += " ORDER BY COALESCE(data_publicacao, created_at) DESC, id DESC"
    cursor.execute(query)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def obter_estatisticas_kpi(incluir_demo=True, db_path=None):
    """Retorna métricas chave para o painel principal."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    filtro_demo = "" if incluir_demo else " WHERE (origem_registo IS NULL OR origem_registo != 'DEMO')"
    and_demo = "" if incluir_demo else " AND (origem_registo IS NULL OR origem_registo != 'DEMO')"

    cursor.execute(f"SELECT COUNT(*) FROM obras{filtro_demo}")
    total_obras = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM obras WHERE origem_registo = 'REAL'")
    obras_reais = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM obras WHERE origem_registo = 'DEMO'")
    obras_demo = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM obras WHERE score >= 75{and_demo}")
    prioritarias = cursor.fetchone()[0]

    cursor.execute(f"""
        SELECT COUNT(*) FROM obras
        WHERE (estado_verificacao IS NULL OR estado_verificacao = 'Por verificar'){and_demo}
    """)
    contactos_por_identificar = cursor.fetchone()[0]

    today = date.today().isoformat()
    cursor.execute("SELECT COUNT(*) FROM tarefas WHERE estado = 'Pendente' AND data_limite < ?", (today,))
    tarefas_atrasadas = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tarefas WHERE estado = 'Pendente' AND data_limite = ?", (today,))
    tarefas_hoje = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alertas_recolha WHERE processado = 0 AND (origem_registo IS NULL OR origem_registo != 'DEMO')")
    alertas_novos = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM obras WHERE tem_conflito = 1")
    obras_com_conflito = cursor.fetchone()[0]

    conn.close()
    return {
        "total_obras": total_obras,
        "obras_reais": obras_reais,
        "obras_demo": obras_demo,
        "prioritarias": prioritarias,
        "contactos_por_identificar": contactos_por_identificar,
        "tarefas_atrasadas": tarefas_atrasadas,
        "tarefas_hoje": tarefas_hoje,
        "alertas_novos": alertas_novos,
        "obras_com_conflito": obras_com_conflito
    }


def inserir_obra(dados_obra, empresas_intervenientes=None, produtos_pemsa=None, db_path=None):
    """Insere uma nova obra com chave estável e estado de verificação explícito."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    dados_obra.setdefault("responsavel_nome", "Por verificar")
    dados_obra.setdefault("responsavel_cargo", "Por verificar")
    dados_obra.setdefault("responsavel_empresa", "Por verificar")
    dados_obra.setdefault("responsavel_contacto", "Por verificar")
    dados_obra.setdefault("estado_verificacao", "Por verificar")
    dados_obra.setdefault("origem_registo", "REAL")
    dados_obra.setdefault("data_publicacao_fonte", dados_obra.get("data_detecao"))
    dados_obra.setdefault("data_consulta_fonte", datetime.now().isoformat(timespec="seconds"))
    dados_obra.setdefault(
        "chave_estavel",
        gerar_chave_estavel_obra(
            dados_obra.get("titulo", ""),
            dados_obra.get("concelho", ""),
            dados_obra.get("distrito", ""),
        )
    )

    cursor.execute("""
    INSERT INTO obras (
        titulo, codigo_ref, chave_estavel, segmento, regiao, distrito, concelho, morada_localizacao,
        lat, lon, fase, status_comercial, score, score_breakdown, prioridade,
        valor_estimado, prazo_previsto, data_detecao, data_publicacao_fonte, data_consulta_fonte,
        fonte_tipo, fonte_nome, fonte_url, resumo, timing_fornecimento, proxima_acao, notas_comerciais,
        responsavel_nome, responsavel_cargo, responsavel_empresa, responsavel_contacto,
        estado_verificacao, origem_registo
    ) VALUES (
        :titulo, :codigo_ref, :chave_estavel, :segmento, :regiao, :distrito, :concelho, :morada_localizacao,
        :lat, :lon, :fase, :status_comercial, :score, :score_breakdown, :prioridade,
        :valor_estimado, :prazo_previsto, :data_detecao, :data_publicacao_fonte, :data_consulta_fonte,
        :fonte_tipo, :fonte_nome, :fonte_url, :resumo, :timing_fornecimento, :proxima_acao, :notas_comerciais,
        :responsavel_nome, :responsavel_cargo, :responsavel_empresa, :responsavel_contacto,
        :estado_verificacao, :origem_registo
    )
    """, dados_obra)
    obra_id = cursor.lastrowid

    if empresas_intervenientes:
        for item in empresas_intervenientes:
            cursor.execute("""
            INSERT OR IGNORE INTO obra_empresas (obra_id, empresa_id, papel, confirmado, estado_verificacao, notas)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                obra_id,
                item['empresa_id'],
                item['papel'],
                item.get('confirmado', 0),
                item.get('estado_verificacao', 'Por verificar'),
                item.get('notas', '')
            ))

    if produtos_pemsa:
        for p in produtos_pemsa:
            cursor.execute("""
            INSERT INTO obra_produtos (obra_id, familia_produto, nivel_potencial, especificacao_detalhe)
            VALUES (?, ?, ?, ?)
            """, (obra_id, p['familia_produto'], p.get('nivel_potencial', 'Potencial Teórico'), p.get('especificacao_detalhe', '')))

    conn.commit()
    conn.close()
    return obra_id


def atualizar_status_obra(obra_id, novo_status, novas_notas=None, db_path=None):
    """Atualiza o estado de pipeline e notas comerciais de uma obra, preservando o trabalho comercial."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    if novas_notas is not None:
        cursor.execute("""
            UPDATE obras SET status_comercial = ?, notas_comerciais = ?, editado_manualmente = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (novo_status, novas_notas, obra_id))
    else:
        cursor.execute("""
            UPDATE obras SET status_comercial = ?, editado_manualmente = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (novo_status, obra_id))
    conn.commit()
    conn.close()


def atualizar_intervenientes_obra(obra_id, responsavel_nome, responsavel_cargo, responsavel_empresa, responsavel_contacto, estado_verificacao="Confirmado por contacto direto", db_path=None):
    """
    Atualiza manualmente os contactos/intervenientes de uma obra e marca `editado_manualmente = 1`
    para que nunca seja sobrescrito automaticamente por extrações futuras.
    """
    if estado_verificacao not in ESTADOS_VERIFICACAO_VALIDOS:
        estado_verificacao = "Por verificar"

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT responsavel_nome, responsavel_empresa, responsavel_contacto FROM obras WHERE id = ?", (obra_id,))
    ant = cur_row = cursor.fetchone()
    val_ant = f"{dict(ant)}" if cur_row else ""

    cursor.execute("""
        UPDATE obras
        SET responsavel_nome = ?, responsavel_cargo = ?, responsavel_empresa = ?, responsavel_contacto = ?,
            estado_verificacao = ?, editado_manualmente = 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (responsavel_nome, responsavel_cargo, responsavel_empresa, responsavel_contacto, estado_verificacao, obra_id))

    cursor.execute("""
        INSERT INTO obra_historico (obra_id, acao, campo, valor_anterior, valor_novo, fonte_nome, fonte_url)
        VALUES (?, 'REVISAO_MANUAL', 'Contactos & Intervenientes', ?, ?, 'Utilizador (Manual)', '')
    """, (obra_id, val_ant, f"{responsavel_nome} | {responsavel_empresa} | {responsavel_contacto} ({estado_verificacao})"))

    conn.commit()
    conn.close()


def resolver_conflito_obra(obra_id, historico_id, aceitar_novo_valor=False, db_path=None):
    """Permite ao utilizador resolver um conflito detetado entre fontes."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM obra_historico WHERE id = ? AND obra_id = ?", (historico_id, obra_id))
    h = cur.fetchone()
    if h:
        h_dict = dict(h)
        campo = h_dict["campo"]
        if aceitar_novo_valor and campo in ("fase", "valor_estimado", "responsavel_empresa", "concelho", "distrito"):
            cur.execute(f"UPDATE obras SET {campo} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (h_dict["valor_novo"], obra_id))
        cur.execute("UPDATE obra_historico SET resolvido = 1 WHERE id = ?", (historico_id,))

    cur.execute("SELECT COUNT(*) FROM obra_historico WHERE obra_id = ? AND acao = 'CONFLITO' AND resolvido = 0", (obra_id,))
    restantes = cur.fetchone()[0]
    if restantes == 0:
        cur.execute("UPDATE obras SET tem_conflito = 0 WHERE id = ?", (obra_id,))

    conn.commit()
    conn.close()


def atualizar_score_obra(obra_id, novo_score, prioridade, breakdown_json, db_path=None):
    """Atualiza pontuação recalculada da obra."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE obras SET score = ?, prioridade = ?, score_breakdown = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (novo_score, prioridade, breakdown_json, obra_id))
    conn.commit()
    conn.close()


def adicionar_tarefa(obra_id, titulo, tipo, data_limite, prioridade="Normal", empresa_id=None, contacto_id=None, db_path=None):
    """Adiciona uma tarefa de seguimento."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO tarefas (obra_id, empresa_id, contacto_id, titulo, tipo, data_limite, prioridade)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (obra_id, empresa_id, contacto_id, titulo, tipo, data_limite, prioridade))
    conn.commit()
    conn.close()


def concluir_tarefa(tarefa_id, resultado, db_path=None):
    """Conclui uma tarefa registando o resultado comercial."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE tarefas SET estado = 'Concluída', resultado_interacao = ?, data_conclusao = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (resultado, tarefa_id))
    conn.commit()
    conn.close()


def marcar_alerta_processado(alerta_id, obra_id=None, db_path=None):
    """Regista que um alerta foi triado pelo utilizador."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE alertas_recolha SET processado = 1, obra_id_gerada = ?
    WHERE id = ?
    """, (obra_id, alerta_id))
    conn.commit()
    conn.close()


def exportar_backup_json(db_path=None):
    """Exporta um backup completo (JSON) das obras, empresas, contactos, tarefas e histórico."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    dados = {}
    for tabela in ["obras", "empresas", "obra_empresas", "contactos", "obra_produtos", "tarefas", "alertas_recolha", "obra_historico", "configuracoes"]:
        cur.execute(f"SELECT * FROM {tabela}")
        dados[tabela] = [dict(r) for r in cur.fetchall()]
    conn.close()
    return json.dumps(dados, ensure_ascii=False, indent=2)
