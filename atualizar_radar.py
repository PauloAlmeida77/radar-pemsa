"""
atualizar_radar.py - Script executável independente da interface Streamlit
para sincronização real e agendada do Radar de Obras PÉMSA.

Utilização:
  python atualizar_radar.py              # Executa sincronização forçada e imprime relatório
  python atualizar_radar.py --json       # Imprime relatório detalhado em formato JSON
  python atualizar_radar.py --auditar    # Imprime relatório de registos DEMO / suspeitos
"""

import sys
import json
import argparse
from database import (
    init_db,
    executar_sincronizacao_radar,
    listar_registos_suspeitos,
)


def main():
    parser = argparse.ArgumentParser(description="Sincronizador autónomo do Radar de Obras PÉMSA")
    parser.add_argument("--json", action="store_true", help="Imprimir resultado em formato JSON")
    parser.add_argument("--auditar", action="store_true", help="Listar registos marcados como DEMO ou Por verificar")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout HTTP por fonte em segundos (default: 10)")
    args = parser.parse_args()

    init_db()

    if args.auditar:
        suspeitos = listar_registos_suspeitos()
        if args.json:
            print(json.dumps(suspeitos, ensure_ascii=False, indent=2))
        else:
            print(f"=== RELATÓRIO DE AUDITORIA DE INTEGRIDADE ({len(suspeitos)} registos) ===")
            for s in suspeitos:
                print(
                    f"- [ID {s['id']}] [{s['origem_registo']} | {s['estado_verificacao']}] "
                    f"{s['codigo_ref']}: {s['titulo']} | Conflito: {s['tem_conflito']}"
                )
        return 0

    relatorio = executar_sincronizacao_radar(forcar=True, modo="AGENDADA", timeout=args.timeout)

    if args.json:
        print(json.dumps(relatorio, ensure_ascii=False, indent=2))
    else:
        print("=================================================================")
        print(f" RADAR PÉMSA — RELATÓRIO DE SINCRONIZAÇÃO ({relatorio['estado_global'].upper()})")
        print("=================================================================")
        print(f"Início:               {relatorio['inicio_ts']}")
        print(f"Fim:                  {relatorio['fim_ts']}")
        print(f"Estado Global:        {relatorio['estado_global']}")
        print(f"Fontes Consultadas:   {relatorio['fontes_consultadas']} (Sucesso: {relatorio['fontes_sucesso']} | Erro: {relatorio['fontes_erro']})")
        print(f"Notícias Encontradas: {relatorio['noticias_encontradas']}")
        print(f"Novas Obras Criadas:  {relatorio['obras_criadas']}")
        print(f"Obras Atualizadas:    {relatorio['obras_atualizadas']}")
        print(f"Duplicados Ignorados: {relatorio['duplicados_ignorados']}")
        print(f"Alertas p/ Validação: {relatorio['alertas_pendentes']}")
        print("-----------------------------------------------------------------")
        for rf in relatorio.get("relatorios_fontes", []):
            status_ic = "OK" if rf["sucesso"] else "ERRO"
            det = f"{len(rf['itens'])} itens ({rf['tempo_ms']} ms)" if rf["sucesso"] else rf["erro"]
            print(f" [{status_ic}] {rf['fonte_nome']}: {det}")
        print("=================================================================")

    # Código de saída 1 apenas se TODAS as fontes falharem
    if relatorio["estado_global"] == "Falha":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
