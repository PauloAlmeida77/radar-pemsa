"""
atualizar_radar.py - Script de atualização periódica automática do Radar PÉMSA.
Pode ser executado via linha de comandos, agendador do Windows ou GitHub Actions.
"""

from datetime import datetime
from database import init_db, verificar_e_executar_sincronizacao_automatica

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] A verificar novas obras para o Radar PÉMSA...")
    init_db()
    atualizou, qtd = verificar_e_executar_sincronizacao_automatica()
    if atualizou:
        print(f"Sucesso: {qtd} novos alertas de obras adicionados ao Radar.")
    else:
        print("Base de dados já se encontra atualizada para o período corrente.")

if __name__ == "__main__":
    main()
