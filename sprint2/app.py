"""
app.py
======
Aplicacao principal (Flask) do Sistema de Separacao de Medicamentos -
Sprint 2: Sistema Inteligente e Integracao Industrial.

Fornece:
  - Dashboard web (HMI/SCADA) em tempo real (/)
  - API REST de controle da simulacao (/api/simulacao/...)
  - API REST de status (sensores, cilindros, imagem da camera) (/api/status)
  - "SAP simulado": endpoints que representam o sistema corporativo
    (/api/sap/registro, /api/sap/estoque, /api/sap/historico, /api/sap/lote/<lote>)

Para executar:
    pip install -r requirements.txt
    python3 app.py
Depois acesse: http://127.0.0.1:5000
"""

import itertools
import threading

from flask import Flask, jsonify, render_template, request

import traceability as tr
from simulation import SimulationEngine

app = Flask(__name__)

tr.init_db("data/rastreabilidade.db")
engine = SimulationEngine(base_url="http://127.0.0.1:5000")

# contador sequencial de "documentos" do SAP simulado
_sap_doc_counter = itertools.count(100000)
_sap_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/")
def dashboard():
    return render_template("dashboard.html")


# ---------------------------------------------------------------------------
# Controle da simulacao
# ---------------------------------------------------------------------------
@app.route("/api/simulacao/iniciar", methods=["POST"])
def iniciar_simulacao():
    started = engine.start()
    return jsonify({"ok": True, "iniciado": started, "running": True})


@app.route("/api/simulacao/parar", methods=["POST"])
def parar_simulacao():
    engine.stop()
    return jsonify({"ok": True, "running": False})


@app.route("/api/simulacao/reset", methods=["POST"])
def reset_simulacao():
    engine.reset()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Status em tempo real (sensores, cilindros, imagem da camera, ultimo item)
# ---------------------------------------------------------------------------
@app.route("/api/status")
def status():
    return jsonify(engine.get_status())


# ---------------------------------------------------------------------------
# "SAP simulado" - sistema corporativo (ERP)
# ---------------------------------------------------------------------------
@app.route("/api/sap/registro", methods=["POST"])
def sap_registro():
    """Endpoint que representa o modulo de Gestao de Estoque do SAP.
    Recebe o JSON gerado pelo controlador da celula e responde com um
    protocolo de confirmacao (numero de documento de material)."""
    payload = request.get_json(force=True)

    with _sap_lock:
        doc_id = next(_sap_doc_counter)
    protocolo = f"SAP-MAT-{doc_id}"

    return jsonify({
        "status": "recebido",
        "protocolo_sap": protocolo,
        "estoque_atualizado": True,
        "deposito": payload.get("deposito_destino"),
        "lote": payload.get("lote"),
    })


@app.route("/api/sap/historico")
def sap_historico():
    lote = request.args.get("lote")
    if lote:
        registros = tr.get_by_lote(lote)
    else:
        registros = tr.get_all()
    return jsonify(registros)


@app.route("/api/sap/estoque")
def sap_estoque():
    return jsonify(tr.get_stats())


@app.route("/api/sap/lote/<lote_id>")
def sap_lote(lote_id):
    return jsonify(tr.get_by_lote(lote_id))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
