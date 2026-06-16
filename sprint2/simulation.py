"""
simulation.py
==============
Motor de Simulacao - orquestra o ciclo completo da celula de separacao:

  Esteira -> Sensor S1 (presenca) -> Sensor S2 (visao computacional)
  -> Logica de decisao -> Atuacao do cilindro (A, B ou nenhum)
  -> Registro de rastreabilidade -> Integracao com SAP (simulado)

Roda em uma thread separada para que a interface (Flask/Dashboard)
permaneca responsiva, expondo o estado atual via `get_status()`.
"""

import random
import threading
import time
import uuid
from datetime import datetime, timezone

import vision_classifier as vc
import traceability as tr
import sap_integration as sap
from pneumatic import PneumaticCylinder


# Proporcoes de geracao de itens (simula a composicao do lote na linha)
DISTRIBUICAO_ITENS = [
    ("Medicamento Tipo 1", 0.45),
    ("Medicamento Tipo 2", 0.45),
    ("Defeito", 0.10),
]

ITENS_POR_LOTE = 6


class SimulationEngine:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.lock = threading.Lock()
        self.running = False
        self.thread = None

        self.cyl_a = PneumaticCylinder("Cilindro A (Tipo 1)", "Valvula 5/2 - Y1/Y2")
        self.cyl_b = PneumaticCylinder("Cilindro B (Tipo 2)", "Valvula 5/2 - Y3/Y4")

        self.contador_itens = 0
        self.lote_atual = self._novo_lote()
        self.itens_no_lote = 0

        self.sensor_s1 = False  # presenca
        self.sensor_s2 = False  # leitura visao

        self.ultimo_item = None
        self.ultima_imagem_b64 = ""
        self.log_sap = []  # ultimas trocas com o SAP

    # ------------------------------------------------------------------
    def _novo_lote(self):
        data = datetime.now().strftime("%Y%m%d")
        seq = random.randint(100, 999)
        return f"LOTE-{data}-{seq}"

    def _sortear_tipo_real(self):
        r = random.random()
        acumulado = 0.0
        for tipo, p in DISTRIBUICAO_ITENS:
            acumulado += p
            if r <= acumulado:
                return tipo
        return DISTRIBUICAO_ITENS[-1][0]

    # ------------------------------------------------------------------
    def start(self):
        with self.lock:
            if self.running:
                return False
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
            return True

    def stop(self):
        with self.lock:
            self.running = False
            return True

    def reset(self):
        with self.lock:
            self.running = False
        time.sleep(0.2)
        tr.reset_db()
        with self.lock:
            self.contador_itens = 0
            self.lote_atual = self._novo_lote()
            self.itens_no_lote = 0
            self.cyl_a = PneumaticCylinder("Cilindro A (Tipo 1)", "Valvula 5/2 - Y1/Y2")
            self.cyl_b = PneumaticCylinder("Cilindro B (Tipo 2)", "Valvula 5/2 - Y3/Y4")
            self.ultimo_item = None
            self.ultima_imagem_b64 = ""
            self.log_sap = []

    # ------------------------------------------------------------------
    def _loop(self):
        while True:
            with self.lock:
                if not self.running:
                    break

            self._processar_item()
            time.sleep(random.uniform(0.6, 1.4))

    # ------------------------------------------------------------------
    def _processar_item(self):
        item_id = str(uuid.uuid4())
        tipo_real = self._sortear_tipo_real()

        # --- Sensor S1: deteccao de presenca ---
        with self.lock:
            self.sensor_s1 = True
        ts_deteccao = tr.now_iso()

        # --- Sensor S2: visao computacional ---
        img = vc.generate_item_image(tipo_real)
        resultado = vc.classify_item(img)
        img_overlay = vc.draw_overlay(img, resultado)
        img_b64 = vc.image_to_base64(img_overlay)

        with self.lock:
            self.sensor_s2 = True
            self.ultima_imagem_b64 = img_b64

        ts_classificacao = tr.now_iso()
        tipo_classificado = resultado["tipo_classificado"]
        confianca = resultado["confianca"]

        # --- Logica de decisao ---
        if tipo_classificado == "Medicamento Tipo 1":
            cilindro = self.cyl_a
            cilindro_label = "Cilindro A"
            destino = "Saida 1 - Medicamento Tipo 1"
        elif tipo_classificado == "Medicamento Tipo 2":
            cilindro = self.cyl_b
            cilindro_label = "Cilindro B"
            destino = "Saida 2 - Medicamento Tipo 2"
        else:
            cilindro = None
            cilindro_label = "Nenhum"
            destino = "Linha de Revisao Manual"

        # gerencia lote
        with self.lock:
            if self.itens_no_lote >= ITENS_POR_LOTE:
                self.lote_atual = self._novo_lote()
                self.itens_no_lote = 0
            lote = self.lote_atual
            self.itens_no_lote += 1
            self.contador_itens += 1

        item = {
            "id": item_id,
            "lote": lote,
            "tipo_real": tipo_real if tipo_real != "Defeito" else "Revisao Manual",
            "tipo_classificado": tipo_classificado,
            "confianca": confianca,
            "status": "Classificado",
            "destino": destino,
            "cilindro": cilindro_label,
            "timestamp_deteccao": ts_deteccao,
            "timestamp_classificacao": ts_classificacao,
            "timestamp_separacao": None,
            "timestamp_registro_sap": None,
            "tempo_ciclo_ms": None,
            "protocolo_sap": None,
        }
        tr.insert_item(item)

        # Campos extras (apenas para o dashboard - nao vao para o SQLite)
        item["scores"] = resultado["scores"]
        item["detalhes"] = resultado["detalhes"]

        # --- Atuacao pneumatica ---
        tempo_ciclo_ms = 0.0
        if cilindro is not None:
            tempo_ciclo = cilindro.ciclo()
            tempo_ciclo_ms = round(tempo_ciclo * 1000, 1)
            status_final = "Separado"
        else:
            time.sleep(0.15)  # tempo simbolico de desvio na esteira p/ revisao
            status_final = "Desviado para Revisao"

        with self.lock:
            self.sensor_s1 = False
            self.sensor_s2 = False

        ts_separacao = tr.now_iso()
        tr.update_item(
            item_id,
            status=status_final,
            timestamp_separacao=ts_separacao,
            tempo_ciclo_ms=tempo_ciclo_ms,
        )
        item["status"] = status_final
        item["timestamp_separacao"] = ts_separacao
        item["tempo_ciclo_ms"] = tempo_ciclo_ms

        # --- Integracao com SAP (simulado) ---
        resposta_sap = sap.enviar_para_sap(item, self.base_url)
        protocolo = resposta_sap.get("protocolo_sap")
        ts_sap = tr.now_iso()
        tr.update_item(
            item_id,
            status="Registrado SAP" if protocolo else item["status"],
            timestamp_registro_sap=ts_sap,
            protocolo_sap=protocolo,
        )
        item["status"] = "Registrado SAP" if protocolo else item["status"]
        item["timestamp_registro_sap"] = ts_sap
        item["protocolo_sap"] = protocolo

        with self.lock:
            self.ultimo_item = item
            self.log_sap.insert(0, {
                "enviado": resposta_sap.get("payload_enviado"),
                "resposta": {k: v for k, v in resposta_sap.items() if k != "payload_enviado"},
            })
            self.log_sap = self.log_sap[:8]

    # ------------------------------------------------------------------
    def get_status(self):
        with self.lock:
            return {
                "running": self.running,
                "contador_itens": self.contador_itens,
                "lote_atual": self.lote_atual,
                "itens_no_lote": self.itens_no_lote,
                "itens_por_lote": ITENS_POR_LOTE,
                "sensor_s1": self.sensor_s1,
                "sensor_s2": self.sensor_s2,
                "cilindro_a": self.cyl_a.estado(),
                "cilindro_b": self.cyl_b.estado(),
                "ultimo_item": self.ultimo_item,
                "ultima_imagem_b64": self.ultima_imagem_b64,
                "log_sap": self.log_sap,
            }
