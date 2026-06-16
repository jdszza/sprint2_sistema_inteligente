# Sprint 2 — Sistema Inteligente de Separação de Medicamentos

Protótipo evoluído do projeto da Sprint 1 (FIAP — Engenharia Mecatrônica /
Pneumática e Hidráulica), agora com:

- **Inteligência (Visão Computacional simulada)** — classificação de itens por
  cor/forma (OpenCV) com nível de confiança.
- **Rastreabilidade** — registro de cada item processado em banco de dados
  SQLite (ID único, lote, tipo, confiança, destino, status, tempos de ciclo,
  protocolo SAP).
- **Integração corporativa (SAP simulado)** — envio de payload JSON estilo
  transação SAP (`MOV_ESTOQUE_AUTOMACAO`) para um endpoint local que simula o
  ERP e responde com protocolo de confirmação.
- **Dashboard SCADA/HMI** — diagrama P&ID animado (esteira, sensores,
  cilindros A e B, válvulas 5/2, unidade FRL, compressor, manômetro),
  painel de visão computacional, indicadores de produção, histórico de
  rastreabilidade e log de integração com o SAP — tudo em tempo real.

---

## 1. Requisitos

- Python 3.10 ou superior
- pip

## 2. Instalação

```bash
# (opcional) crie um ambiente virtual
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# instale as dependências
pip install -r requirements.txt
```

## 3. Execução

```bash
python3 app.py
```

O servidor inicia em `http://127.0.0.1:5000` (acessível também via
`http://localhost:5000`). Abra esse endereço no navegador para ver o
dashboard.

Ao iniciar, o sistema cria automaticamente o banco de dados de
rastreabilidade em `data/rastreabilidade.db` (vazio na primeira execução).

## 4. Usando o dashboard

No topo da tela há três botões que controlam a simulação da célula
pneumática:

| Botão     | Ação |
|-----------|------|
| **INICIAR** | Liga a esteira/simulação. A cada ciclo, um item sintético é gerado, "fotografado" pelo Sensor S2 e classificado pela visão computacional. Conforme o resultado, o Cilindro A (Tipo 1), o Cilindro B (Tipo 2) ou o desvio de Revisão Manual (baixa confiança) é acionado. Cada item é gravado na rastreabilidade e enviado ao SAP simulado. |
| **PARAR**   | Pausa a simulação no estado atual (sensores, cilindros e contadores ficam congelados). |
| **RESET**   | Para a simulação e zera todos os contadores, lotes e o histórico de rastreabilidade (apaga os registros do banco de dados). |

### Painéis do dashboard

- **Diagrama P&ID — Célula Pneumática**: representação esquemática da célula
  (esteira, sensores S1/S2, válvulas 5/2 vias, cilindros de dupla ação A e B,
  unidade FRL, compressor e linha de ar a 0,6 MPa). Os elementos acendem/
  animam em tempo real conforme a simulação avança.
- **Visão Computacional · Sensor S2**: mostra a "imagem" capturada do item
  atual, o resultado da classificação (Tipo 1 / Tipo 2 / Revisão Manual), o
  percentual de confiança e os scores intermediários (cobertura de cor,
  aspect ratio, área do contorno) usados pelo algoritmo.
- **Indicadores de Produção**: totais por tipo, itens em revisão manual,
  acurácia da IA, progresso do lote atual, tempo médio de ciclo dos
  cilindros e contadores de acionamento.
- **Rastreabilidade — Histórico de Itens**: tabela com cada item processado
  (ID, lote, tipo, confiança, destino, status e protocolo SAP).
- **Integração Corporativa (SAP simulado)**: log das últimas transações
  enviadas ao "SAP" (request) e das respostas recebidas (response), em
  formato JSON.

## 5. Endpoints da API

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Dashboard (HMI/SCADA) |
| POST | `/api/simulacao/iniciar` | Inicia a simulação |
| POST | `/api/simulacao/parar` | Pausa a simulação |
| POST | `/api/simulacao/reset` | Reseta contadores e rastreabilidade |
| GET | `/api/status` | Status em tempo real (sensores, cilindros, item atual, imagem, log SAP) |
| POST | `/api/sap/registro` | Endpoint do "SAP simulado" que recebe o payload e devolve o protocolo |
| GET | `/api/sap/historico` | Histórico completo de itens rastreados (aceita `?lote=`) |
| GET | `/api/sap/estoque` | Estatísticas agregadas (totais, acurácia, tempo médio de ciclo, lotes) |
| GET | `/api/sap/lote/<lote_id>` | Itens de um lote específico |

## 6. Estrutura do projeto

```
sprint2/
├── app.py                 # Aplicação Flask (rotas, dashboard, API, SAP simulado)
├── simulation.py          # Motor da simulação (thread em background)
├── vision_classifier.py   # Geração e classificação de imagens (visão computacional)
├── pneumatic.py           # Modelo dos cilindros pneumáticos (ciclo, sensores)
├── traceability.py         # Persistência da rastreabilidade (SQLite)
├── sap_integration.py     # Montagem e envio do payload para o SAP simulado
├── templates/
│   └── dashboard.html     # Layout do dashboard (diagrama P&ID em SVG)
├── static/
│   ├── style.css           # Tema visual SCADA/HMI
│   └── dashboard.js        # Lógica de atualização do dashboard (polling)
├── data/                   # Banco de dados SQLite (criado automaticamente)
└── requirements.txt
```

## 7. Observações

- Todos os dados (imagens dos itens, sensores, válvulas, integração SAP) são
  **simulados em software**, conforme proposto na Sprint 2. Não há hardware
  real conectado.
- O tempo de ciclo de cada cilindro (~0,8 s) e a pressão de trabalho
  (0,6 MPa) seguem os parâmetros técnicos definidos no relatório do projeto.
