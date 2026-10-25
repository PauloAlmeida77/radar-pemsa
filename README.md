# ⚡ Radar de Obras PÉMSA 🇵🇹

Sistema de Inteligência Comercial e Prospeção Ativa de Obras em Portugal.

O **Radar de Obras PÉMSA** descobre, valida e acompanha oportunidades de obras em Portugal a partir de fontes públicas, separando rigorosamente **evidência verificável** de dados por confirmar, e ajudando a responder a cinco perguntas fundamentais:
1. **Que obra é?**
2. **Onde fica e em que fase está?**
3. **Quem promove, projeta, constrói ou instala?**
4. **Que produtos PÉMSA poderão ser utilizados?**
5. **Ainda há tempo para entrar no fornecimento?**

---

## 🛡️ Integridade de Dados e Estados de Verificação

- **Separação entre Dados Reais e Demonstração (`origem_registo`):**
  - `REAL`: Oportunidades recolhidas de fontes públicas verificáveis (com URL específico, nome da fonte, data real de publicação e timestamp de consulta) ou validadas comercialmente.
  - `DEMO`: Registos de demonstração iniciais preservados para consulta/teste, filtráveis na barra lateral (`Incluir registos de demonstração (DEMO)` — desativado por defeito).
- **Estados de Verificação (`estado_verificacao`):**
  - `Por verificar`: Campos ainda sem evidência documental direta na fonte (ex.: projetista, instalador elétrico ou contacto nominal ainda não divulgado).
  - `Confirmado por fonte`: Intervenientes, valores ou adjudicações citados explicitamente na notícia ou anúncio oficial.
  - `Confirmado por contacto direto`: Dados introduzidos ou validados manualmente pela equipa comercial PÉMSA (protegidos contra substituição automática).
- **Preservação e Resolução de Conflitos:**
  - Notas comerciais, tarefas, estado do pipeline e contactos confirmados **nunca** são sobrescritos pela sincronização automática.
  - Quando uma nova fonte apresenta um valor divergente (ex.: atualização de orçamento ou fase), o Radar regista um `CONFLITO` no histórico da obra e apresenta opções na **Ficha da Obra** para manter o valor atual ou adotar o valor da nova fonte.

---

## 🏗️ Estrutura da Aplicação (As 7 Áreas)

1. **📊 Painel Inicial (Dashboard):**
   - KPIs comerciais em tempo real: Total de Obras Ativas, Oportunidades Prioritárias (Score $\ge$ 75), Contactos por Verificar e Tarefas Atrasadas.
   - **Oportunidade do Dia em Destaque** e estado da última sincronização real.
2. **🔎 Pesquisa de Obras (Radar & Filtros):**
   - Filtros por Segmento, Região, Fase da Obra, Prioridade e Origem (`REAL` / `DEMO`).
3. **🗺️ Mapa de Portugal (Geolocalização Interativa):**
   - Mapa interativo com código de cores por prioridade comercial.
4. **📋 Ficha da Obra & Dossiê 360°:**
   - **Motor de Pontuação PÉMSA (0 a 100)**, **Cadeia de Decisão** (Promotor, Projetista MEP, Empreiteiro Geral e Instalador Elétrico), **Produtos PÉMSA**, **Resolução de Conflitos** e **Histórico de Alterações e Fontes (`obra_historico`)**.
5. **🏢 Empresas & Decisores:**
   - Diretório de intervenientes e contactos com indicação explícita do estado de verificação (`Por verificar`, `Confirmado por fonte`, `Confirmado por contacto direto`).
6. **📅 Plano Comercial & Tarefas (CRM de Prospeção):**
   - Gestão de chamadas, visitas, apresentações técnicas e propostas (*Em Atraso*, *Para Hoje*, *Próximas*).
7. **📡 Motor de Recolha, Auditoria & Exportação:**
   - **Feed de Alertas Pendentes:** Notícias recolhidas que mencionam projetos ou investimentos mas aguardam validação de localização ou tipologia antes de serem promovidas a obra.
   - **Registos Suspeitos / DEMO:** Relatório de auditoria dos registos de demonstração com opção de saneamento de atribuições não verificadas.
   - **Assistente de Extração de Texto** e **Exportação Excel (.xlsx) / Backup JSON**.

---

## 🚀 Execução Manual

### 1. Iniciar a Interface Web (Streamlit)

```powershell
cd C:\Users\PauloAlmeida\.gemini\antigravity\scratch\radar_pemsa
streamlit run app.py
```

Na barra lateral, o botão **🔄 Atualizar Agora** executa uma sincronização real imediata (sem bloqueio por semana ISO) e apresenta o relatório completo:
- Hora de início e fim;
- Estado global (`Sucesso`, `Sucesso parcial` ou `Falha`);
- Fontes consultadas, com sucesso e com erro;
- Novas notícias encontradas, novas obras criadas, obras existentes atualizadas, duplicados ignorados e alertas pendentes de validação.

### 2. Executar o Script de Sincronização via Linha de Comandos (CLI)

O script `atualizar_radar.py` funciona de forma totalmente independente do Streamlit:

```powershell
# Sincronização completa com relatório detalhado na consola
python atualizar_radar.py

# Executar auditoria/separação de dados DEMO antes de sincronizar
python atualizar_radar.py --auditar

# Saída estruturada em JSON (ideal para integrações/logs)
python atualizar_radar.py --json
```

Códigos de saída (`exit code`):
- `0`: `Sucesso` ou `Sucesso parcial` (pelo menos uma fonte pública respondeu com sucesso).
- `1`: `Falha` (todas as fontes falharam ou erro crítico).

---

## ⏰ Atualização Automática Agendada

### Opção A: GitHub Actions (Execução Diária na Cloud — Recomendado)

O repositório inclui o workflow `.github/workflows/sync_radar.yml`, configurado para correr:
- **Automaticamente todos os dias às 07:00 UTC** (`cron: '0 7 * * *'`);
- **Manualmente a qualquer momento** no separador **Actions → Sincronizacao Diaria Radar PEMSA → Run workflow**.

**Permissões necessárias no GitHub:**
1. No repositório GitHub (`Settings` → `Actions` → `General` → `Workflow permissions`), garantir que a opção **Read and write permissions** está selecionada (o próprio workflow já declara `permissions: contents: write`).
2. Quando a sincronização deteta novas obras, atualizações ou alertas, o workflow faz commit e push automático de `radar_pemsa.db`, atualizando também a aplicação no Streamlit Cloud.

### Opção B: Agendador de Tarefas do Windows (Execução Local)

Para agendar a execução diária no computador local (Windows) às 08:00 sem precisar de ter o browser aberto:

```powershell
schtasks /Create /SC DAILY /TN "RadarPEMSA_SyncDiario" /TR "python C:\Users\PauloAlmeida\.gemini\antigravity\scratch\radar_pemsa\atualizar_radar.py" /ST 08:00 /F
```

Para testar a tarefa imediatamente:
```powershell
schtasks /Run /TN "RadarPEMSA_SyncDiario"
```

---

## 🔐 Variáveis de Ambiente, Segredos e Persistência

### Variáveis de Ambiente e Segredos (`st.secrets` / `os.environ`)

| Variável / Segredo | Descrição | Valor por Defeito |
| :--- | :--- | :--- |
| `PEMSA_PIN` (ou `PASSWORD`) | Código PIN de acesso à aplicação Streamlit. Deve ser configurado em **Streamlit Cloud → App Settings → Secrets** (`PEMSA_PIN = "xxxx"`) ou variável de ambiente. | `2026` (fallback local) |
| `RADAR_DB_PATH` | Caminho personalizado para o ficheiro SQLite (útil para volumes persistentes ou testes isolados). | `./radar_pemsa.db` |

### Persistência em Streamlit Cloud vs. Local
- No ambiente local, o ficheiro SQLite `radar_pemsa.db` persiste diretamente no disco.
- No **Streamlit Community Cloud**, o sistema de ficheiros do contentor é efémero aquando de *reboots*, mas **persiste todas as alterações commitadas no repositório GitHub** (como as efetuadas pelo GitHub Actions diário).
- Caso crie ou edite notas/tarefas diretamente na interface Cloud e pretenda guardar uma cópia de segurança imediata antes de um *redeploy*, utilize o botão **💾 Exportar Backup Completo (JSON)** na página **7. Motor de Recolha → Exportar Excel & Backup JSON**.

---

## 🧪 Testes Automatizados

O projeto inclui testes unitários e de integração em `tests/test_radar_sync.py` que validam (com respostas simuladas e base de dados temporária isolada):
1. Deduplicação de obras e criação apenas com evidência verificável (retendo notícias vagas como alertas pendentes);
2. Atualização de obras existentes, preservação de contactos/notas manuais e deteção/resolução de conflitos entre fontes;
3. Isolamento de falhas de fontes (`HTTP 500`, `URLError`, XML malformado, feed vazio) e estados `Sucesso parcial` vs `Falha`;
4. Execução forçada repetida sem bloqueio por semana ISO.

Para correr a suite de testes:

```powershell
python -m unittest discover -s tests -v
```
