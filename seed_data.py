"""
seed_data.py - Gestão de dados iniciais e migração não-destrutiva de integridade.
Não insere nem repõe dados de demonstração no arranque normal da aplicação.
"""

import os
from database import init_db, auditar_e_separar_dados_demonstracao


def popular_dados_iniciais(permitir_demo=False, db_path=None):
    """
    No arranque normal (`permitir_demo=False`), garante apenas a inicialização
    do esquema e a auditoria/separação não-destrutiva entre registos DEMO e REAL,
    preservando integralmente todas as obras, tarefas, notas comerciais e histórico existentes.
    Nunca volta a inserir dados de demonstração automaticamente no arranque.
    """
    init_db(db_path=db_path)
    auditar_e_separar_dados_demonstracao(db_path=db_path)

    # Só permite criar sementes de demonstração se explicitamente solicitado por variável ou argumento
    if not permitir_demo and os.environ.get("SEED_DEMO_DATA", "0") != "1":
        return False

    return False


if __name__ == "__main__":
    popular_dados_iniciais(permitir_demo=False)
    print("Auditoria não-destrutiva de integridade concluída com sucesso.")
