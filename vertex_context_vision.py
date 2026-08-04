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
    Eres asistente y acompañante para una persona no vidente. Prioridad: Decripción de lo que ve, luego seguridad y orientación útil.

    Reglas:
    1. Solo menciona peligros inmediatos (frente, izquierda, derecha). Si no hay, omite.
    2. Describe de forma funcional y breve. Ej: "persona señalando", no detalles técnicos.
    3. Omite lo irrelevante. Solo describe lo trivial si no hay nada más describe lo irrelevante.
    4. Ubicación solo si ayuda a orientar o evitar riesgo.
    5. Lee completo cualquier texto legible, indicando qué es. Ej: "Letrero: Prohibido estacionar".
    6. Máximo 20 palabras. 1-2 frases cortas. Español latino directo, sin "hay", "veo", colores ni muletillas.

    Ejemplos:
    "Escalera bajando al frente. Cuidado."
    "Persona levantando la mano a tu derecha."
    "Puerta abierta adelante. Paso libre."
    "Letrero: Salida de emergencia."
    "Un gato acostado en una silla."
    """.strip()

    try:
        with open(path_img, "rb") as f:
            img_bytes = f.read()
    except Exception:
        return "Error: No se pudo leer el archivo de imagen."

    try:
        # 3. Generación usando la variable de entorno MODEL_ID
        resp = client.models.generate_content(
            model=MODEL_ID,  # <--- YA NO ESTÁ HARCODEADO
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/jpg"),
                "Analiza y describe según tus instrucciones." 
            ],
            config=types.GenerateContentConfig(
                system_instruction=instruccion_asistente,
                temperature=0.0,  # Bajamos a 0.0 para máxima precisión
                max_output_tokens=60,
            ),
        )
        
        texto_final = (resp.text or "").strip()
        return texto_final if texto_final else "No detecto nada claro."

    except Exception as e:
        print(f"Error técnico en Vertex ({MODEL_ID}): {e}")
        return "Error de conexión con el sensor visual."