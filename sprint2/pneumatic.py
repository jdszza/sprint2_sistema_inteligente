"""
pneumatic.py
============
Modulo dos atuadores pneumaticos (evolucao da Sprint 1).

Mantem a logica de Cilindro de Dupla Acao acionado por valvula
direcional 5/2 vias (solenoide), mas agora com:
  - Medicao real de tempo de ciclo (avanco/recuo)
  - Estado dos sensores de fim de curso (avancado/recuado)
  - Contador de acionamentos e tempo medio de ciclo (para o
    criterio de Eficiencia/Otimizacao)
"""

import time


class PneumaticCylinder:
    """Representa um cilindro pneumatico de dupla acao controlado por
    valvula direcional 5/2 vias com acionamento por solenoide."""

    def __init__(self, name: str, valve_label: str, tempo_avanco=0.35, tempo_recuo=0.35):
        self.name = name
        self.valve_label = valve_label   # ex: "Valvula 5/2 - Y1/Y2"
        self.position = "Recuado"        # Recuado | Avancado
        self.sensor_recuado = True
        self.sensor_avancado = False
        self.tempo_avanco = tempo_avanco
        self.tempo_recuo = tempo_recuo
        self.acionamentos = 0
        self.tempos_ciclo = []

    def ciclo(self):
        """Executa um ciclo completo: avanca (empurra o item) e recua."""
        inicio = time.time()

        # Avanco - solenoide energiza Y_avanco
        self.position = "Avancando"
        self.sensor_recuado = False
        time.sleep(self.tempo_avanco)
        self.position = "Avancado"
        self.sensor_avancado = True

        time.sleep(0.1)  # tempo de contato/empurrao do item

        # Recuo - solenoide energiza Y_recuo
        self.position = "Recuando"
        self.sensor_avancado = False
        time.sleep(self.tempo_recuo)
        self.position = "Recuado"
        self.sensor_recuado = True

        tempo_total = time.time() - inicio
        self.acionamentos += 1
        self.tempos_ciclo.append(tempo_total)
        return tempo_total

    def tempo_medio_ciclo(self):
        if not self.tempos_ciclo:
            return 0.0
        return sum(self.tempos_ciclo) / len(self.tempos_ciclo)

    def estado(self):
        return {
            "nome": self.name,
            "valvula": self.valve_label,
            "posicao": self.position,
            "sensor_recuado": self.sensor_recuado,
            "sensor_avancado": self.sensor_avancado,
            "acionamentos": self.acionamentos,
            "tempo_medio_ciclo_ms": round(self.tempo_medio_ciclo() * 1000, 1),
        }
