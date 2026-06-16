"""
traceability.py
================
Modulo de Rastreabilidade (criterio 3 do Sprint 2).

Cada item processado pela linha recebe:
  - ID unico (UUID4)
  - Numero de lote (lote)
  - Tipo classificado pela visao computacional
  - Tipo real (rotulo de referencia, usado so para metricas de acuracia)
  - Confianca da classificacao
  - Destino (Saida 1 / Saida 2 / Revisao Manual)
  - Cilindro acionado
  - Status (Detectado -> Classificado -> Separado -> Registrado SAP)
  - Timestamps de cada etapa
  - Tempo de ciclo (ms)

Os registros sao persistidos em SQLite, permitindo consulta de
historico completo por ID, por lote ou geral - cumprindo o requisito
de "Historico completo + identificacao unica".
"""

import sqlite3
import threading
from datetime import datetime, timezone

DB_PATH = "data/rastreabilidade.db"

_lock = threading.Lock()


def _connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str = DB_PATH):
    global DB_PATH
    DB_PATH = path
    conn = _connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS itens (
            id TEXT PRIMARY KEY,
            lote TEXT NOT NULL,
            tipo_real TEXT,
            tipo_classificado TEXT,
            confianca REAL,
            status TEXT,
            destino TEXT,
            cilindro TEXT,
            timestamp_deteccao TEXT,
            timestamp_classificacao TEXT,
            timestamp_separacao TEXT,
            timestamp_registro_sap TEXT,
            tempo_ciclo_ms REAL,
            protocolo_sap TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def insert_item(item: dict):
    with _lock:
        conn = _connect()
        conn.execute(
            """
            INSERT INTO itens (id, lote, tipo_real, tipo_classificado, confianca,
                                status, destino, cilindro, timestamp_deteccao,
                                timestamp_classificacao, timestamp_separacao,
                                timestamp_registro_sap, tempo_ciclo_ms, protocolo_sap)
            VALUES (:id, :lote, :tipo_real, :tipo_classificado, :confianca,
                    :status, :destino, :cilindro, :timestamp_deteccao,
                    :timestamp_classificacao, :timestamp_separacao,
                    :timestamp_registro_sap, :tempo_ciclo_ms, :protocolo_sap)
            """,
            item,
        )
        conn.commit()
        conn.close()


def update_item(item_id: str, **fields):
    if not fields:
        return
    with _lock:
        conn = _connect()
        cols = ", ".join(f"{k} = :{k}" for k in fields)
        fields["id"] = item_id
        conn.execute(f"UPDATE itens SET {cols} WHERE id = :id", fields)
        conn.commit()
        conn.close()


def get_all(limit: int = 200):
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM itens ORDER BY timestamp_deteccao DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_by_lote(lote: str):
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM itens WHERE lote = ? ORDER BY timestamp_deteccao DESC", (lote,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    conn = _connect()
    total = conn.execute("SELECT COUNT(*) AS c FROM itens").fetchone()["c"]

    por_tipo = conn.execute(
        "SELECT tipo_classificado AS tipo, COUNT(*) AS qtd FROM itens GROUP BY tipo_classificado"
    ).fetchall()

    acertos = conn.execute(
        """SELECT COUNT(*) AS c FROM itens
           WHERE tipo_classificado = tipo_real
             AND tipo_classificado != 'Revisao Manual'"""
    ).fetchone()["c"]

    classificaveis = conn.execute(
        "SELECT COUNT(*) AS c FROM itens WHERE tipo_classificado != 'Revisao Manual'"
    ).fetchone()["c"]

    tempo_medio = conn.execute(
        "SELECT AVG(tempo_ciclo_ms) AS m FROM itens WHERE tempo_ciclo_ms IS NOT NULL AND tempo_ciclo_ms > 0"
    ).fetchone()["m"]

    lotes = conn.execute(
        "SELECT DISTINCT lote FROM itens ORDER BY lote DESC"
    ).fetchall()

    conn.close()

    acuracia = (acertos / classificaveis * 100) if classificaveis else 0.0

    return {
        "total_processado": total,
        "por_tipo": {r["tipo"]: r["qtd"] for r in por_tipo},
        "acuracia_classificacao_pct": round(acuracia, 1),
        "tempo_medio_ciclo_ms": round(tempo_medio, 1) if tempo_medio else 0.0,
        "lotes": [r["lote"] for r in lotes],
    }


def reset_db():
    with _lock:
        conn = _connect()
        conn.execute("DELETE FROM itens")
        conn.commit()
        conn.close()
