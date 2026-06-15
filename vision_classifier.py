"""
vision_classifier.py
=====================
Modulo de "Visao Computacional Simulada" para o Sistema de Separacao de
Medicamentos (Sprint 2).

Como nao ha uma camera fisica disponivel, este modulo SIMULA o sensor S2
(camera de visao computacional) de duas formas:

1. generate_item_image(): gera uma imagem sintetica de um item sobre a
   esteira (simulando o frame capturado pela camera).
2. classify_item(): processa essa imagem com tecnicas REAIS de visao
   computacional via OpenCV (espaco de cor HSV, segmentacao por cor,
   deteccao de contornos, analise de forma/aspect ratio) para classificar
   o item em "Medicamento Tipo 1", "Medicamento Tipo 2" ou
   "Revisao Manual" (quando a confianca da classificacao e baixa).

A "verdade de campo" (tipo_real) e mantida separadamente apenas para fins
de avaliacao de acuracia do sistema (nao e usada pelo classificador) -
ela representa, por exemplo, um rotulo conhecido em um cenario de testes.
"""

import cv2
import numpy as np
import random
import base64

# ---------------------------------------------------------------------------
# Configuracoes de imagem
# ---------------------------------------------------------------------------
IMG_W, IMG_H = 320, 160
BELT_COLOR = (148, 138, 122)       # BGR - cor da esteira (cinza azulado)
BELT_STRIPE_COLOR = (120, 112, 98)  # listras da esteira

# Cores "reais" dos itens (BGR)
COLOR_TIPO_1 = (210, 130, 40)   # azul -> Medicamento Tipo 1 (comprimido redondo)
COLOR_TIPO_2 = (40, 90, 225)    # laranja/vermelho -> Medicamento Tipo 2 (capsula)
COLOR_DEFEITO = (120, 150, 120)  # tom acinzentado/esverdeado -> item nao identificado

# Faixas HSV usadas pelo classificador
HSV_RANGES = {
    "Medicamento Tipo 1": ((95, 80, 60), (135, 255, 255)),   # azul
    "Medicamento Tipo 2": ((0, 90, 90), (20, 255, 255)),     # laranja/vermelho
}

CONFIDENCE_THRESHOLD = 0.55  # abaixo disso -> Revisao Manual


def _draw_belt(img):
    img[:] = BELT_COLOR
    for x in range(0, IMG_W, 18):
        cv2.line(img, (x, 0), (x, IMG_H), BELT_STRIPE_COLOR, 2)
    return img


def generate_item_image(tipo_real: str, seed: int | None = None):
    """Gera uma imagem sintetica (simulando o frame da camera) contendo um
    item sobre a esteira.

    Parameters
    ----------
    tipo_real : str
        "Medicamento Tipo 1", "Medicamento Tipo 2" ou "Defeito"
    seed : int, opcional
        Semente para reprodutibilidade.

    Returns
    -------
    np.ndarray
        Imagem BGR (uint8) de dimensao (IMG_H, IMG_W, 3)
    """
    rng = random.Random(seed)
    img = np.zeros((IMG_H, IMG_W, 3), dtype=np.uint8)
    _draw_belt(img)

    cx, cy = IMG_W // 2 + rng.randint(-25, 25), IMG_H // 2 + rng.randint(-8, 8)

    if tipo_real == "Medicamento Tipo 1":
        # comprimido redondo (azul)
        radius = rng.randint(22, 28)
        color = tuple(int(c + rng.randint(-12, 12)) for c in COLOR_TIPO_1)
        cv2.circle(img, (cx, cy), radius, color, -1)
        cv2.circle(img, (cx, cy), radius, (30, 30, 30), 1)

    elif tipo_real == "Medicamento Tipo 2":
        # capsula alongada (laranja/vermelho)
        axes = (rng.randint(34, 42), rng.randint(15, 20))
        angle = rng.randint(-10, 10)
        color = tuple(int(c + rng.randint(-12, 12)) for c in COLOR_TIPO_2)
        cv2.ellipse(img, (cx, cy), axes, angle, 0, 360, color, -1)
        cv2.ellipse(img, (cx, cy), axes, angle, 0, 360, (30, 30, 30), 1)

    else:
        # "Defeito": item com cor/forma ambigua (gera baixa confianca)
        shape_type = rng.choice(["circulo_pequeno", "borrado", "cor_indefinida"])
        if shape_type == "circulo_pequeno":
            radius = rng.randint(8, 12)
            cv2.circle(img, (cx, cy), radius, COLOR_DEFEITO, -1)
        elif shape_type == "borrado":
            radius = rng.randint(18, 24)
            overlay = img.copy()
            cv2.circle(overlay, (cx, cy), radius, COLOR_DEFEITO, -1)
            img = cv2.addWeighted(overlay, 0.35, img, 0.65, 0)
        else:
            axes = (rng.randint(20, 28), rng.randint(18, 26))
            cv2.ellipse(img, (cx, cy), axes, 0, 0, 360, COLOR_DEFEITO, -1)

    # ruido leve para simular condicoes reais de iluminacao/camera
    noise = np.random.randint(0, 10, (IMG_H, IMG_W, 3), dtype=np.uint8)
    img = cv2.add(img, noise)

    return img


def classify_item(img):
    """Classifica o item presente na imagem usando segmentacao HSV +
    analise de forma (contornos).

    Returns
    -------
    dict com:
        tipo_classificado : str
        confianca : float (0-1)
        detalhes : dict (cor dominante, aspect ratio, area do contorno)
        bbox : (x, y, w, h) ou None
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    img_area = IMG_W * IMG_H
    expected_item_area = 2000.0  # area aproximada esperada de um item "tipico"

    scores = {}
    details = {}
    bboxes = {}

    for tipo, (lower, upper) in HSV_RANGES.items():
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        # remove ruido pequeno
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            scores[tipo] = 0.0
            details[tipo] = {"area": 0, "aspect_ratio": 0.0, "cor_pct": 0.0}
            bboxes[tipo] = None
            continue

        c = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(c)
        x, y, w, h = cv2.boundingRect(c)
        aspect_ratio = max(w, h) / max(1, min(w, h))

        cor_pct = min(1.0, area / expected_item_area)

        if tipo == "Medicamento Tipo 1":
            # quanto mais proximo de um circulo (aspect ~1), maior o score de forma
            shape_score = max(0.0, 1.0 - abs(aspect_ratio - 1.0))
        else:
            # quanto mais alongado (capsula), maior o score de forma
            shape_score = min(1.0, max(0.0, (aspect_ratio - 1.0) / 1.0))

        score = 0.6 * cor_pct + 0.4 * shape_score
        scores[tipo] = round(min(1.0, score), 4)
        details[tipo] = {
            "area": int(area),
            "aspect_ratio": round(float(aspect_ratio), 2),
            "cor_pct": round(cor_pct, 2),
        }
        bboxes[tipo] = (x, y, w, h)

    # melhor candidato
    melhor_tipo = max(scores, key=scores.get)
    melhor_score = scores[melhor_tipo]

    if melhor_score < CONFIDENCE_THRESHOLD:
        tipo_classificado = "Revisao Manual"
        bbox = bboxes.get(melhor_tipo)
    else:
        tipo_classificado = melhor_tipo
        bbox = bboxes.get(melhor_tipo)

    return {
        "tipo_classificado": tipo_classificado,
        "confianca": round(float(melhor_score), 3),
        "scores": scores,
        "detalhes": details,
        "bbox": bbox,
    }


def draw_overlay(img, classification):
    """Desenha bounding box + rotulo de classificacao sobre a imagem,
    simulando a saida visual do sistema de visao computacional."""
    out = img.copy()
    bbox = classification.get("bbox")
    tipo = classification["tipo_classificado"]
    conf = classification["confianca"]

    color_map = {
        "Medicamento Tipo 1": (255, 180, 60),
        "Medicamento Tipo 2": (60, 140, 255),
        "Revisao Manual": (0, 215, 255),
    }
    box_color = color_map.get(tipo, (255, 255, 255))

    if bbox:
        x, y, w, h = bbox
        cv2.rectangle(out, (x - 4, y - 4), (x + w + 4, y + h + 4), box_color, 2)

    label = f"{tipo} ({conf*100:.0f}%)"
    cv2.putText(out, label, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 1, cv2.LINE_AA)
    return out


def image_to_base64(img) -> str:
    """Converte uma imagem OpenCV (BGR) para string base64 (PNG), para
    envio ao dashboard via JSON."""
    success, buf = cv2.imencode(".png", img)
    if not success:
        return ""
    return base64.b64encode(buf).decode("ascii")


# ---------------------------------------------------------------------------
# Teste rapido (executar: python3 vision_classifier.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    for tipo_real in ["Medicamento Tipo 1", "Medicamento Tipo 2", "Defeito"]:
        for i in range(3):
            img = generate_item_image(tipo_real, seed=i)
            result = classify_item(img)
            print(f"tipo_real={tipo_real:22s} -> classificado={result['tipo_classificado']:20s} "
                  f"confianca={result['confianca']:.2f} scores={result['scores']}")
