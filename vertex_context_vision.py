#!/usr/bin/python3
import os
import time
from google import genai
from google.genai import types
from logger import get_logger

log = get_logger("vertex")

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL_ID = os.environ.get("VERTEX_GEMINI_MODEL", "gemini-2.5-flash-lite")

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
)


def describir_o_leer(path_img: str, cycle_id=None) -> str:
    instruccion_asistente = """
    Eres los ojos de una persona no vidente. Tu prioridad es describir la escena de forma util y completa, no solo advertir peligros.

    Reglas:
    1. Primero menciona cualquier peligro u obstaculo inmediato (frente, izquierda, derecha) si existe.
    2. Despues describe la escena: que objetos, personas o superficies relevantes hay y como estan ubicados entre si (izquierda/derecha/cerca/lejos).
    3. Se especifico: en vez de "una superficie" di que tipo (piso, mesa, pared, escalon). En vez de "un objeto", nombralo si lo reconoces.
    4. Lee completo cualquier texto legible (letreros, pantallas, documentos), indicando que es. Ej: "Letrero: Prohibido estacionar".
    5. Español latino directo, sin "hay", "veo", colores ni muletillas. Frases cortas, pero pueden ser 2-3 si hace falta para ser claro.
    6. Máximo 40 palabras.

    Ejemplos:
    "Escalera bajando al frente. Cuidado."
    "Persona a tu derecha, levantando la mano para saludar."
    "Puerta abierta adelante, paso libre. Piso de baldosa."
    "Letrero: Salida de emergencia."
    "Un gato acostado en una silla de madera, a tu izquierda."
    """.strip()

    try:
        with open(path_img, "rb") as f:
            img_bytes = f.read()
    except Exception as e:
        log.error(f"[{cycle_id}] No se pudo leer imagen {path_img}: {e}")
        return "Error: No se pudo leer el archivo de imagen."

    t0 = time.time()
    try:
        resp = client.models.generate_content(
            model=MODEL_ID,
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                "Analiza y describe según tus instrucciones."
            ],
            config=types.GenerateContentConfig(
                system_instruction=instruccion_asistente,
                temperature=0.0,
                max_output_tokens=120,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )

        dt = time.time() - t0
        texto_final = (resp.text or "").strip()
        if texto_final:
            log.info(f'[{cycle_id}] OK ({MODEL_ID}, {dt:.2f}s): "{texto_final}"')
            return texto_final
        else:
            log.warning(f"[{cycle_id}] Respuesta vacia ({MODEL_ID}, {dt:.2f}s)")
            return "No detecto nada claro."

    except Exception as e:
        log.error(f"[{cycle_id}] Fallo ({MODEL_ID}, {time.time()-t0:.2f}s): {e}")
        return "Error de conexión con el sensor visual."
