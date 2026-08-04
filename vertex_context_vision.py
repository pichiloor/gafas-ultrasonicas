#!/usr/bin/python3
import os
from google import genai
from google.genai import types

# --- CONFIGURACIÓN GLOBAL (Fuera de la función para mayor velocidad) ---
# Aquí cargamos tus variables de entorno una sola vez
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
# Aquí insertamos tu variable para el modelo:
MODEL_ID = os.environ.get("VERTEX_GEMINI_MODEL", "gemini-2.5-flash-lite")

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
)

def describir_o_leer(path_img: str) -> str:
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
    except Exception:
        return "Error: No se pudo leer el archivo de imagen."

    try:
        resp = client.models.generate_content(
            model=MODEL_ID,
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                "Analiza y describe según tus instrucciones."
            ],
            config=types.GenerateContentConfig(
                system_instruction=instruccion_asistente,
                temperature=0.0,  # Bajamos a 0.0 para máxima precisión
                max_output_tokens=120,
                # thinking_budget=0: evita que modelos no-lite (gemini-2.5-flash,
                # -pro) gasten el presupuesto de tokens "pensando" internamente
                # y devuelvan texto vacío. Inofensivo para -lite.
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )

        texto_final = (resp.text or "").strip()
        return texto_final if texto_final else "No detecto nada claro."

    except Exception as e:
        print(f"Error técnico en Vertex ({MODEL_ID}): {e}")
        return "Error de conexión con el sensor visual."
