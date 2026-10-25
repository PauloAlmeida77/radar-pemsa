"""
test_radar_sync.py - Testes unitários e de integração para o Radar de Obras PÉMSA.
Testa com respostas HTTP simuladas (sem depender nem inventar sucesso de rede real):
1. Deduplicação de obras (chave estável e similaridade).
2. Atualização seletiva de campos, preservação de dados manuais/tarefas e deteção de conflitos.
3. Isolamento de falhas de fontes (Sucesso, Sucesso parcial e Falha total).
4. Execução forçada ("Atualizar Agora") sem bloqueio por semana ISO ou janela temporal.
5. Separação entre obras com evidência verificável e alertas pendentes, e preservação da data real de publicação.
"""

import os
import sys
import tempfile
import unittest
import requests

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from database import (
    init_db,
    executar_sincronizacao_radar,
    listar_obras,
    obter_obra_por_id,
    listar_alertas,
    atualizar_status_obra,
    atualizar_intervenientes_obra,
    adicionar_tarefa,
)


class MockResponse:
    """Resposta HTTP simulada para testes determinísticos."""
    def __init__(self, status_code=200, content=b""):
        self.status_code = status_code
        self.content = content if isinstance(content, bytes) else content.encode("utf-8")


class MockSession:
    """Sessão HTTP simulada que mapeia URLs a respostas ou exceções."""
    def __init__(self, route_map):
        self.route_map = route_map

    def get(self, url, timeout=8, headers=None, verify=True):
        handler = self.route_map.get(url)
        if handler is None:
            return MockResponse(status_code=404, content=b"Not Found")
        if isinstance(handler, Exception):
            raise handler
        if callable(handler):
            return handler(url)
        return handler


def criar_rss_xml(itens):
    """Gera um payload XML RSS 2.0 válido a partir de uma lista de dicionários."""
    items_xml = ""
    for it in itens:
        pub = f"<pubDate>{it['pubDate']}</pubDate>" if it.get("pubDate") else ""
        src = f"<source>{it.get('source', 'Jornal Teste')}</source>"
        desc = f"<description>{it.get('description', '')}</description>"
        items_xml += f"""
        <item>
            <title>{it['title']}</title>
            <link>{it['link']}</link>
            {pub}
            {src}
            {desc}
        </item>
        """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Feed Simulado Radar PEMSA</title>
            {items_xml}
        </channel>
    </rss>""".encode("utf-8")


class TestRadarPemsaSync(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_radar.db")
        init_db(db_path=self.db_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_1_deduplicacao_obras(self):
        """Verifica que a mesma obra recolhida duas vezes não gera duplicados."""
        fonte_teste = [{
            "id": "f_teste_1",
            "nome": "Fonte Simulada 1",
            "tipo": "Imprensa",
            "metodo": "rss",
            "url": "https://mock.local/rss1"
        }]
        xml_payload = criar_rss_xml([{
            "title": "Município de Braga lança concurso público para construção de novo hospital em Braga",
            "link": "https://mock.local/noticias/hospital-braga-concurso-2026",
            "pubDate": "Mon, 12 Oct 2026 09:30:00 GMT",
            "description": "Concurso público para a empreitada de construção do novo hospital em Braga."
        }])
        sess = MockSession({"https://mock.local/rss1": MockResponse(200, xml_payload)})

        # 1.ª execução: deve criar 1 obra
        rel1 = executar_sincronizacao_radar(forcar=True, fontes=fonte_teste, session=sess, db_path=self.db_path)
        self.assertEqual(rel1["estado_global"], "Sucesso")
        self.assertEqual(rel1["obras_criadas"], 1)

        # 2.ª execução com a mesma notícia: deve ignorar duplicado (0 criadas, >=1 duplicado ignorado)
        rel2 = executar_sincronizacao_radar(forcar=True, fontes=fonte_teste, session=sess, db_path=self.db_path)
        self.assertEqual(rel2["obras_criadas"], 0)
        self.assertEqual(rel2["obras_atualizadas"], 0)
        self.assertGreaterEqual(rel2["duplicados_ignorados"], 1)

        obras = listar_obras(db_path=self.db_path)
        self.assertEqual(len(obras), 1)
        # Verificar que a data de publicação guardada é a data real do RSS (2026-10-12) e não a data de consulta
        self.assertEqual(obras[0]["data_publicacao_fonte"], "2026-10-12")

    def test_2_atualizacao_campos_preservacao_e_conflitos(self):
        """
        Verifica que:
        - Campos 'Por verificar' são atualizados quando surge nova evidência.
        - Tarefas, notas comerciais, estado do pipeline e contactos confirmados manualmente são preservados.
        - Quando uma nova fonte diverge de um valor confirmado, é registado um CONFLITO sem sobrescrever silenciosamente.
        """
        fonte_cfg = [{
            "id": "f_teste_upd",
            "nome": "Fonte Simulada Evolução",
            "tipo": "Imprensa",
            "metodo": "rss",
            "url": "https://mock.local/rss_upd"
        }]

        # Passo 1: Notícia inicial sem valor estimado explícito
        xml_1 = criar_rss_xml([{
            "title": "Abertura de concurso público para nova fábrica industrial em Aveiro",
            "link": "https://mock.local/noticias/fabrica-aveiro-fase1",
            "pubDate": "Tue, 13 Oct 2026 10:00:00 GMT",
            "description": "Lançamento de concurso público para nova fábrica industrial em Aveiro."
        }])
        rel1 = executar_sincronizacao_radar(
            forcar=True,
            fontes=fonte_cfg,
            session=MockSession({"https://mock.local/rss_upd": MockResponse(200, xml_1)}),
            db_path=self.db_path
        )
        self.assertEqual(rel1["obras_criadas"], 1)
        obra_id = listar_obras(db_path=self.db_path)[0]["id"]

        # Utilizador adiciona nota comercial, tarefa e confirma um contacto manualmente
        atualizar_status_obra(obra_id, "Contacto Feito", "Reunião marcada com o promotor.", db_path=self.db_path)
        adicionar_tarefa(obra_id, "Enviar catálogo Rejiband", "Email", "2026-10-30", db_path=self.db_path)
        atualizar_intervenientes_obra(
            obra_id,
            responsavel_nome="Departamento Técnico Confirmado",
            responsavel_cargo="Direção de Engenharia",
            responsavel_empresa="Promotor Aveiro Industrial",
            responsavel_contacto="+351 234 000 000",
            estado_verificacao="Confirmado por contacto direto",
            db_path=self.db_path
        )

        # Passo 2: Nova notícia sobre a mesma obra traz o valor de 25 milhões de euros
        xml_2 = criar_rss_xml([{
            "title": "Concurso público para nova fábrica industrial em Aveiro avaliado em 25 milhões de euros",
            "link": "https://mock.local/noticias/fabrica-aveiro-fase2",
            "pubDate": "Wed, 14 Oct 2026 11:00:00 GMT",
            "description": "Empreitada da nova fábrica industrial em Aveiro tem investimento de 25 milhões de euros."
        }])
        rel2 = executar_sincronizacao_radar(
            forcar=True,
            fontes=fonte_cfg,
            session=MockSession({"https://mock.local/rss_upd": MockResponse(200, xml_2)}),
            db_path=self.db_path
        )
        self.assertEqual(rel2["obras_atualizadas"], 1)

        obra_apos_upd = obter_obra_por_id(obra_id, db_path=self.db_path)
        self.assertIn("25 M€", obra_apos_upd["valor_estimado"])
        # Verificar preservação de dados manuais e tarefas
        self.assertEqual(obra_apos_upd["status_comercial"], "Contacto Feito")
        self.assertEqual(obra_apos_upd["notas_comerciais"], "Reunião marcada com o promotor.")
        self.assertEqual(obra_apos_upd["responsavel_contacto"], "+351 234 000 000")
        self.assertEqual(len(obra_apos_upd["tarefas"]), 1)

        # Passo 3: Testar deteção de CONFLITO numa obra não bloqueada manualmente quando duas fontes divergem no valor
        xml_conf_1 = criar_rss_xml([{
            "title": "Adjudicada construção de plataforma logística em Leiria por 12 milhões de euros",
            "link": "https://mock.local/noticias/logistica-leiria-1",
            "pubDate": "Thu, 15 Oct 2026 08:00:00 GMT",
            "description": "Adjudicação da plataforma logística em Leiria por 12 milhões de euros."
        }])
        executar_sincronizacao_radar(
            forcar=True,
            fontes=fonte_cfg,
            session=MockSession({"https://mock.local/rss_upd": MockResponse(200, xml_conf_1)}),
            db_path=self.db_path
        )
        obras_leiria = [o for o in listar_obras(db_path=self.db_path) if o["concelho"] == "Leiria"]
        self.assertEqual(len(obras_leiria), 1)
        id_leiria = obras_leiria[0]["id"]

        # Segunda fonte diverge no valor (30 milhões de euros em vez de 12 milhões)
        xml_conf_2 = criar_rss_xml([{
            "title": "Construção de plataforma logística em Leiria custará 30 milhões de euros",
            "link": "https://mock.local/noticias/logistica-leiria-2",
            "pubDate": "Fri, 16 Oct 2026 09:00:00 GMT",
            "description": "Empreitada da plataforma logística em Leiria avaliada em 30 milhões de euros."
        }])
        executar_sincronizacao_radar(
            forcar=True,
            fontes=fonte_cfg,
            session=MockSession({"https://mock.local/rss_upd": MockResponse(200, xml_conf_2)}),
            db_path=self.db_path
        )
        obra_leiria_det = obter_obra_por_id(id_leiria, db_path=self.db_path)
        # O valor original (12 M€) não foi silenciosamente apagado, e tem_conflito foi ativado
        self.assertIn("12 M€", obra_leiria_det["valor_estimado"])
        self.assertEqual(obra_leiria_det["tem_conflito"], 1)
        acoes_hist = [h["acao"] for h in obra_leiria_det["historico"]]
        self.assertIn("CONFLITO", acoes_hist)

    def test_3_falha_fontes_isolamento_e_estados(self):
        """
        Verifica que:
        - Uma fonte indisponível (Timeout ou HTTP 500) não impede a consulta às restantes ('Sucesso parcial').
        - Quando todas as fontes falham, o estado é 'Falha' (nunca falso sucesso).
        """
        fontes_mistas = [
            {"id": "f_ok", "nome": "Fonte Funcional", "tipo": "Imprensa", "metodo": "rss", "url": "https://mock.local/ok"},
            {"id": "f_timeout", "nome": "Fonte Lenta", "tipo": "Imprensa", "metodo": "rss", "url": "https://mock.local/timeout"},
            {"id": "f_500", "nome": "Fonte Erro 500", "tipo": "Imprensa", "metodo": "rss", "url": "https://mock.local/err500"},
        ]
        xml_ok = criar_rss_xml([{
            "title": "Início das obras de nova central fotovoltaica em Évora de 18 milhões de euros",
            "link": "https://mock.local/noticias/solar-evora-2026",
            "pubDate": "Fri, 16 Oct 2026 12:00:00 GMT",
            "description": "Arranque das obras da nova central fotovoltaica em Évora."
        }])
        sess_parcial = MockSession({
            "https://mock.local/ok": MockResponse(200, xml_ok),
            "https://mock.local/timeout": requests.exceptions.Timeout("Read timed out"),
            "https://mock.local/err500": MockResponse(500, b"Internal Server Error"),
        })

        rel_parcial = executar_sincronizacao_radar(
            forcar=True, fontes=fontes_mistas, session=sess_parcial, db_path=self.db_path
        )
        self.assertEqual(rel_parcial["estado_global"], "Sucesso parcial")
        self.assertEqual(rel_parcial["fontes_consultadas"], 3)
        self.assertEqual(rel_parcial["fontes_sucesso"], 1)
        self.assertEqual(rel_parcial["fontes_erro"], 2)
        self.assertEqual(rel_parcial["obras_criadas"], 1)
        self.assertEqual(len(rel_parcial["erros"]), 2)

        # Agora todas as fontes falham -> Estado tem de ser 'Falha'
        sess_falha = MockSession({
            "https://mock.local/ok": requests.exceptions.ConnectionError("DNS failure"),
            "https://mock.local/timeout": requests.exceptions.Timeout("Timeout"),
            "https://mock.local/err500": MockResponse(503, b"Service Unavailable"),
        })
        rel_falha = executar_sincronizacao_radar(
            forcar=True, fontes=fontes_mistas, session=sess_falha, db_path=self.db_path
        )
        self.assertEqual(rel_falha["estado_global"], "Falha")
        self.assertEqual(rel_falha["fontes_sucesso"], 0)
        self.assertEqual(rel_falha["fontes_erro"], 3)

    def test_4_execucao_forcada_e_alertas_pendentes(self):
        """
        Verifica que:
        - `forcar=True` executa sempre, mesmo imediatamente após uma sincronização anterior.
        - Notícias vagas apenas com 'construção' ou 'investimento' sem localização/obra concreta
          ficam retidas como Alertas Pendentes e não criam obras falsas.
        """
        fonte_cfg = [{
            "id": "f_alerta",
            "nome": "Fonte Geral",
            "tipo": "Imprensa",
            "metodo": "rss",
            "url": "https://mock.local/rss_geral"
        }]
        xml_vago = criar_rss_xml([{
            "title": "Setor da construção e empreitadas regista crescimento de investimento este ano",
            "link": "https://mock.local/noticias/setor-construcao-geral",
            "pubDate": "Sat, 17 Oct 2026 15:00:00 GMT",
            "description": "Análise macroeconómica sobre licenciamento e construção civil."
        }])
        sess = MockSession({"https://mock.local/rss_geral": MockResponse(200, xml_vago)})

        # 1.ª sincronização
        rel1 = executar_sincronizacao_radar(forcar=True, fontes=fonte_cfg, session=sess, db_path=self.db_path)
        self.assertTrue(rel1["executado"])
        self.assertEqual(rel1["obras_criadas"], 0)
        self.assertEqual(rel1["alertas_pendentes"], 1)

        alertas = listar_alertas(apenas_nao_processados=True, db_path=self.db_path)
        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0]["data_publicacao"], "2026-10-17")

        # 2.ª sincronização imediata com forcar=True não pode ser bloqueada pela janela temporal
        rel2 = executar_sincronizacao_radar(forcar=True, fontes=fonte_cfg, session=sess, db_path=self.db_path)
        self.assertTrue(rel2["executado"])
        self.assertEqual(rel2["estado_global"], "Sucesso")


if __name__ == "__main__":
    unittest.main()
