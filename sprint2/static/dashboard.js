/* ==========================================================================
   Dashboard - Linha de Separacao Automatizada (Sprint 2)
   Logica de atualizacao em tempo real (polling de API REST Flask)
   ========================================================================== */

const CONFIDENCE_THRESHOLD = 0.55;

const TIPO_LABELS = {
  "Medicamento Tipo 1": "Medicamento Tipo 1",
  "Medicamento Tipo 2": "Medicamento Tipo 2",
  "Revisao Manual": "Revisão Manual",
};

const TIPO_BADGE_CLASS = {
  "Medicamento Tipo 1": "tipo1",
  "Medicamento Tipo 2": "tipo2",
  "Revisao Manual": "revisao",
};

const STATUS_BADGE_CLASS = {
  "Classificado": "status-classificado",
  "Separado": "status-separado",
  "Registrado SAP": "status-registrado",
  "Desviado para Revisao": "status-revisao",
};

const CONF_COLORS = {
  "Medicamento Tipo 1": "var(--accent-blue)",
  "Medicamento Tipo 2": "var(--accent-orange)",
  "Revisao Manual": "var(--accent-amber)",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function $(id) {
  return document.getElementById(id);
}

function setClass(id, cls, on) {
  const el = $(id);
  if (el) el.classList.toggle(cls, on);
}

function setOpacity(id, value) {
  const el = $(id);
  if (el) el.style.opacity = value;
}

function fmtPct(value) {
  return `${(value * 100).toFixed(1)}%`;
}

function fmtTime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("pt-BR", { hour12: false });
  } catch (e) {
    return "—";
  }
}

function shortId(id) {
  if (!id) return "—";
  return id.split("-")[0];
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// Coloriza um objeto JSON para exibicao no log SAP
function highlightJSON(obj) {
  const json = escapeHtml(JSON.stringify(obj, null, 2));
  return json.replace(
    /(&quot;.*?&quot;)(\s*:)?|\b(true|false|null)\b|(-?\d+(?:\.\d+)?)/g,
    (match, str, colon, bool, num) => {
      if (str) {
        return colon ? `<span class="json-key">${str}</span>${colon}` : `<span class="json-string">${str}</span>`;
      }
      if (bool) return `<span class="json-bool">${bool}</span>`;
      if (num) return `<span class="json-number">${num}</span>`;
      return match;
    }
  );
}

// ---------------------------------------------------------------------------
// Atualizacao do diagrama PID + status geral
// ---------------------------------------------------------------------------
function updatePID(status) {
  // Status pill
  const pill = $("status-pill");
  const text = $("status-text");
  if (status.running) {
    pill.classList.add("running");
    pill.classList.remove("stopped");
    text.textContent = "EM EXECUÇÃO";
  } else {
    pill.classList.remove("running");
    pill.classList.add("stopped");
    text.textContent = "PARADO";
  }
  $("btn-start").disabled = status.running;
  $("btn-stop").disabled = !status.running;

  // Lote
  $("pid-lote").textContent = status.lote_atual || "—";

  // Sensores S1 / S2 / Revisao
  setClass("sensor-s1", "on", !!status.sensor_s1);
  setClass("sensor-s2", "on", !!status.sensor_s2);

  const item = status.ultimo_item;
  const tipo = item ? item.tipo_classificado : null;

  setOpacity("item-tipo1", tipo === "Medicamento Tipo 1" ? 1 : 0);
  setOpacity("item-tipo2", tipo === "Medicamento Tipo 2" ? 1 : 0);
  setOpacity("item-revisao", tipo === "Revisao Manual" ? 1 : 0);
  setClass("sensor-revisao", "on", tipo === "Revisao Manual");

  // Cilindro A
  updateCylinder(status.cilindro_a, "cylA-piston", "lineA-avanco", "lineA-recuo",
    "sensorA-rec", "sensorA-adv", "valve-v1");

  // Cilindro B
  updateCylinder(status.cilindro_b, "cylB-piston", "lineB-avanco", "lineB-recuo",
    "sensorB-rec", "sensorB-adv", "valve-v2");

  // Rede pneumatica (compressor / suprimento)
  setClass("compressor-group", "running", !!status.running);
  setClass("supply-line", "active", !!status.running);
  setClass("line-compressor-frl", "active", !!status.running);
  setClass("line-supply-v1", "active", !!status.running);
  setClass("line-supply-v2", "active", !!status.running);
}

function updateCylinder(cyl, pistonId, lineAvancoId, lineRecuoId, sensorRecId, sensorAdvId, valveId) {
  if (!cyl) return;
  const avancando = cyl.posicao === "Avancando" || cyl.posicao === "Avancado";

  setClass(pistonId, "extended", avancando);
  setClass(lineAvancoId, "active", avancando);
  setClass(lineRecuoId, "active", !avancando);
  setClass(sensorRecId, "on", !!cyl.sensor_recuado);
  setClass(sensorAdvId, "on", !!cyl.sensor_avancado);
  setClass(valveId, "active", avancando);
}

// ---------------------------------------------------------------------------
// Atualizacao do painel de Visao Computacional
// ---------------------------------------------------------------------------
function updateVision(status) {
  const item = status.ultimo_item;
  const img = $("vision-img");

  if (status.ultima_imagem_b64) {
    img.src = "data:image/png;base64," + status.ultima_imagem_b64;
    img.style.display = "block";
  }

  if (!item) {
    $("vision-tipo").textContent = "Aguardando…";
    $("vision-conf").textContent = "—";
    $("vision-confbar").style.width = "0%";
    $("vision-scores").innerHTML = "";
    $("vision-ts").textContent = "—";
    return;
  }

  const tipoLabel = TIPO_LABELS[item.tipo_classificado] || item.tipo_classificado;
  const color = CONF_COLORS[item.tipo_classificado] || "var(--accent-cyan)";

  $("vision-tipo").textContent = tipoLabel;
  $("vision-tipo").style.color = color;
  $("vision-conf").textContent = `confiança ${fmtPct(item.confianca)}`;

  const bar = $("vision-confbar");
  bar.style.width = fmtPct(item.confianca);
  bar.style.background = color;

  $("vision-ts").textContent = `classificado às ${fmtTime(item.timestamp_classificacao)}`;

  // Tabela de scores detalhados (saida do classificador OpenCV)
  const scores = item.scores || {};
  const detalhes = item.detalhes || {};
  let melhorTipo = null;
  let melhorScore = -1;
  for (const t of Object.keys(scores)) {
    if (scores[t] > melhorScore) {
      melhorScore = scores[t];
      melhorTipo = t;
    }
  }

  const rows = [];
  if ("Medicamento Tipo 1" in scores) {
    rows.push(["Score · Medicamento Tipo 1", scores["Medicamento Tipo 1"].toFixed(3)]);
  }
  if ("Medicamento Tipo 2" in scores) {
    rows.push(["Score · Medicamento Tipo 2", scores["Medicamento Tipo 2"].toFixed(3)]);
  }
  if (melhorTipo && detalhes[melhorTipo]) {
    const d = detalhes[melhorTipo];
    rows.push(["Área do contorno (px²)", d.area]);
    rows.push(["Aspect ratio (forma)", d.aspect_ratio.toFixed(2)]);
    rows.push(["Cobertura de cor", d.cor_pct.toFixed(2)]);
  }
  rows.push(["Limiar de confiança (S2)", CONFIDENCE_THRESHOLD.toFixed(2)]);

  $("vision-scores").innerHTML = rows
    .map(([label, value]) => `<tr><td>${label}</td><td>${value}</td></tr>`)
    .join("");
}

// ---------------------------------------------------------------------------
// Atualizacao do log de integracao SAP (a partir do /api/status)
// ---------------------------------------------------------------------------
function updateSapLog(status) {
  const log = status.log_sap || [];
  const container = $("sap-log");

  if (log.length === 0) {
    container.innerHTML = '<div class="empty-hint">Aguardando eventos de integração…</div>';
    return;
  }

  container.innerHTML = log
    .map((entry) => {
      const resposta = entry.resposta || {};
      const erro = resposta.status === "erro_comunicacao";
      const protocolo = resposta.protocolo_sap || (erro ? "ERRO DE COMUNICAÇÃO" : "—");
      const payload = entry.enviado || {};
      const combined = { request: payload, response: resposta };
      return `
        <div class="sap-entry">
          <div class="sap-entry-head">
            <span>${protocolo}</span>
            <span>${escapeHtml(payload.lote || "")}</span>
          </div>
          <pre>${highlightJSON(combined)}</pre>
        </div>`;
    })
    .join("");
}

// ---------------------------------------------------------------------------
// Atualizacao do painel de Indicadores (/api/sap/estoque)
// ---------------------------------------------------------------------------
function updateStats(stats) {
  const porTipo = stats.por_tipo || {};
  $("stat-tipo1").textContent = porTipo["Medicamento Tipo 1"] || 0;
  $("stat-tipo2").textContent = porTipo["Medicamento Tipo 2"] || 0;
  $("stat-revisao").textContent = porTipo["Revisao Manual"] || 0;
  $("stat-acuracia").textContent = `${stats.acuracia_classificacao_pct.toFixed(1)}%`;
  $("stat-total").textContent = `${stats.total_processado} itens`;
  $("kv-ciclo").textContent = `${stats.tempo_medio_ciclo_ms.toFixed(1)} ms`;
  $("kv-lotes").textContent = (stats.lotes || []).length;
}

function updateBatchProgress(status) {
  const atual = status.itens_no_lote || 0;
  const total = status.itens_por_lote || 1;
  $("lote-atual").textContent = status.lote_atual || "—";
  $("lote-progress-label").textContent = `${atual} / ${total}`;
  $("lote-progress-bar").style.width = `${Math.min(100, (atual / total) * 100)}%`;
}

function updateCylinderCounters(status) {
  $("kv-acionA").textContent = status.cilindro_a ? status.cilindro_a.acionamentos : 0;
  $("kv-acionB").textContent = status.cilindro_b ? status.cilindro_b.acionamentos : 0;
}

// ---------------------------------------------------------------------------
// Atualizacao da tabela de Rastreabilidade (/api/sap/historico)
// ---------------------------------------------------------------------------
function updateTrace(records) {
  $("trace-count").textContent = `${records.length} registros`;

  if (records.length === 0) {
    $("trace-body").innerHTML =
      '<tr><td colspan="8" class="empty-hint">Nenhum item processado ainda. Clique em "Iniciar" para começar a simulação.</td></tr>';
    return;
  }

  $("trace-body").innerHTML = records
    .map((r) => {
      const tipoCls = TIPO_BADGE_CLASS[r.tipo_classificado] || "";
      const tipoLabel = TIPO_LABELS[r.tipo_classificado] || r.tipo_classificado;
      const statusCls = STATUS_BADGE_CLASS[r.status] || "";
      const protocolo = r.protocolo_sap || "—";

      return `
        <tr>
          <td title="${escapeHtml(r.id)}">${shortId(r.id)}</td>
          <td>${escapeHtml(r.lote)}</td>
          <td><span class="badge ${tipoCls}">${tipoLabel}</span></td>
          <td>${fmtPct(r.confianca)}</td>
          <td>${escapeHtml(r.destino || "—")}</td>
          <td><span class="badge ${statusCls}">${escapeHtml(r.status)}</span></td>
          <td>${escapeHtml(protocolo)}</td>
          <td>${fmtTime(r.timestamp_deteccao)}</td>
        </tr>`;
    })
    .join("");
}

// ---------------------------------------------------------------------------
// Polling
// ---------------------------------------------------------------------------
async function pollStatus() {
  try {
    const resp = await fetch("/api/status");
    const status = await resp.json();
    updatePID(status);
    updateVision(status);
    updateSapLog(status);
    updateBatchProgress(status);
    updateCylinderCounters(status);
  } catch (e) {
    console.error("Erro ao consultar /api/status:", e);
  }
}

async function pollEstoque() {
  try {
    const resp = await fetch("/api/sap/estoque");
    const stats = await resp.json();
    updateStats(stats);
  } catch (e) {
    console.error("Erro ao consultar /api/sap/estoque:", e);
  }
}

async function pollHistorico() {
  try {
    const resp = await fetch("/api/sap/historico");
    const records = await resp.json();
    updateTrace(records);
  } catch (e) {
    console.error("Erro ao consultar /api/sap/historico:", e);
  }
}

function pollFast() {
  pollStatus();
}

function pollSlow() {
  pollEstoque();
  pollHistorico();
}

// ---------------------------------------------------------------------------
// Botoes de controle
// ---------------------------------------------------------------------------
$("btn-start").addEventListener("click", async () => {
  await fetch("/api/simulacao/iniciar", { method: "POST" });
  pollFast();
});

$("btn-stop").addEventListener("click", async () => {
  await fetch("/api/simulacao/parar", { method: "POST" });
  pollFast();
});

$("btn-reset").addEventListener("click", async () => {
  await fetch("/api/simulacao/reset", { method: "POST" });
  pollFast();
  pollSlow();
});

// ---------------------------------------------------------------------------
// Inicializacao
// ---------------------------------------------------------------------------
pollFast();
pollSlow();
setInterval(pollFast, 1000);
setInterval(pollSlow, 2000);
