"""
sap_integration.py
===================
Modulo de Integracao com Sistema Corporativo (criterio 4 do Sprint 2).

Simula a comunicacao do controlador da celula de separacao com um
sistema ERP/SAP via API REST + JSON. Como nao existe um SAP real
disponivel, este modulo implementa um "SAP simulado" (mock) que roda
dentro da propria aplicacao Flask (endpoints /api/sap/...), e este
arquivo contem as funcoes que MONTAM o payload JSON e fazem a
requisicao HTTP para esses endpoints - exatamente como seria feito
para um SAP real (troca apenas a URL base).

Fluxo simulado:
  1. O controlador da celula gera um payload JSON com os dados do item
     (id, lote, tipo, confianca, destino, status, timestamps).
  2. Esse payload e enviado via POST para /api/sap/registro (endpoint
     que representa o modulo de Gestao de Estoque/Qualidade do SAP).
  3. O "SAP" responde com um protocolo de confirmacao (numero de
     documento de material) e o status de atualizacao de estoque.
  4. A resposta e registrada na rastreabilidade (protocolo_sap).
"""

import requests
from datetime import datetime, timezone


def montar_payload(item: dict) -> dict:
    """Monta o payload JSON enviado ao sistema corporativo (SAP),
    seguindo um formato inspirado em uma transacao de movimento de
    estoque (ex: MIGO/MB1B simplificado)."""
    return {
        "documento": "MOV_ESTOQUE_AUTOMACAO",
        "id_medicamento": item["id"],
        "lote": item["lote"],
        "material": item["tipo_classificado"],
        "confianca_classificacao": item["confianca"],
        "centro": "CD-SP-01",
        "deposito_destino": item["destino"],
        "cilindro_acionado": item["cilindro"],
        "status_operacional": item["status"],
        "tempo_ciclo_ms": item["tempo_ciclo_ms"],
        "timestamp_evento": datetime.now(timezone.utc).isoformat(),
    }


def enviar_para_sap(item: dict, base_url: str, timeout: float = 2.0) -> dict:
    """Envia o payload JSON para o endpoint do SAP simulado e retorna a
    resposta (ou um erro tratado caso o endpoint nao responda)."""
    payload = montar_payload(item)
    try:
        resp = requests.post(f"{base_url}/api/sap/registro", json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        data["payload_enviado"] = payload
        return data
    except requests.RequestException as exc:
        return {
            "status": "erro_comunicacao",
            "mensagem": str(exc),
            "payload_enviado": payload,
        }
