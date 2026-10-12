# ⚡ Radar de Obras PÉMSA 🇵🇹

Sistema de Inteligência Comercial e Prospeção Ativa de Obras em Portugal.

O **Radar de Obras PÉMSA** transforma notícias, editais e concursos públicos em **oportunidades comerciais qualificadas**, ajudando a responder a cinco perguntas fundamentais:
1. **Que obra é?**
2. **Onde fica e em que fase está?**
3. **Quem promove, projeta, constrói ou instala?**
4. **Que produtos PÉMSA poderão ser utilizados?**
5. **Ainda há tempo para entrar no fornecimento?**

---

## 🏗️ Estrutura da Aplicação (As 7 Áreas)

1. **📊 Painel Inicial (Dashboard):**
   - KPIs comerciais em tempo real: Novas Obras, Oportunidades Prioritárias (Score $\ge$ 75), Contactos em Falta e Tarefas Atrasadas.
   - **Oportunidade do Dia em Destaque:** Apresenta a obra com melhor pontuação e timing, destacando a próxima ação comercial imediata.
   - Tarefas urgentes e distribuição de obras por segmento industrial.

2. **🔎 Pesquisa de Obras (Radar & Filtros):**
   - Filtros múltiplos: Segmento (Data Centers, Hospitais, Indústria, Logística, Hotéis, Energia), Região (Norte, Centro, Sul, Ilhas), Fase da Obra e Prioridade.
   - Visualização em Cartões Comerciais ou Tabela com exportação CSV.

3. **🗺️ Mapa de Portugal (Geolocalização Interativa):**
   - Mapa com as obras localizadas em Portugal Continental, Madeira e Açores.
   - Cores indicativas de prioridade: Verde (Alta $\ge$ 75), Amarelo (Média 50–74) e Cinzento (< 50).

4. **📋 Ficha da Obra & Dossiê 360°:**
   - **Motor de Pontuação PÉMSA (0 a 100):** Breakdown transparente com os 5 critérios estratégicos:
     - *Fase da Obra* (máx. 30 pts)
     - *Compatibilidade PÉMSA* (máx. 25 pts)
     - *Acesso aos Decisores* (máx. 20 pts)
     - *Timing de Fornecimento* (máx. 15 pts)
     - *Adequação Geográfica* (máx. 10 pts)
   - **Cadeia de Decisão:** Promotor / Dono, Projetista MEP, Empreiteiro Geral e Instalador Elétrico, com contactos mapeados.
   - **Produtos PÉMSA:** Classificação entre *Potencial Teórico*, *Compatibilidade Confirmada* e *Oportunidade Validada* para caminhos em chapa (Pemsaband), varão (Rejiband / Rejiband Rapide), PVC, tubos, bucins e suportes.
   - Gestão do estado de pipeline e agendamento de tarefas.

5. **🏢 Empresas & Decisores:**
   - Diretório de intervenientes da construção em Portugal.
   - Visualização de todas as obras onde cada empresa participa e respetivos decisores técnicos/compras.

6. **📅 Plano Comercial & Tarefas (CRM de Prospeção):**
   - Gestão de chamadas, visitas, apresentações técnicas e propostas.
   - Divisão em tarefas *Em Atraso*, *Para Hoje* e *Próximas*.

7. **📡 Motor de Recolha, Alertas & Exportação:**
   - **Feed de Alertas:** Rastreio de anúncios do Portal BASE, TED e imprensa industrial, com aprovação em 1 clique.
   - **Assistente IA de Extração:** Caixa para colar texto de qualquer notícia ou caderno de encargos; o motor analisa automaticamente e preenche a ficha da obra.
   - **Exportação Excel (.xlsx):** Download da lista completa para trabalho offline.

---

## 🚀 Como Executar a Aplicação

Para iniciar o Radar no seu computador:

```powershell
# 1. Navegue até à pasta do projeto
cd C:\Users\PauloAlmeida\.gemini\antigravity\scratch\radar_pemsa

# 2. Inicie o servidor Streamlit
streamlit run app.py
```

A aplicação abrirá automaticamente no seu browser (por defeito em `http://localhost:8501`).

---

## 📁 Estrutura de Ficheiros

- `app.py`: Aplicação web principal em Streamlit com interface gráfica interativa.
- `database.py`: Camada de dados em SQLite (`radar_pemsa.db`) com tabelas de obras, intervenientes, contactos, produtos e tarefas.
- `scoring.py`: Algoritmo de cálculo de pontuação comercial (0–100) com justificação técnica.
- `pemsa_catalog.py`: Matriz técnica dos produtos PÉMSA (Rejiband, Pemsaband, PVC, tubos, bucins) e critérios de aplicação.
- `scrapers.py`: Motor de recolha de portais públicos e extrator inteligente de texto.
- `seed_data.py`: População com projetos de referência em Portugal (Sines, Lisboa, Famalicão, Castanheira, Comporta, Madeira, Maia).
