#!/usr/bin/python3
import os
import re
import textwrap
import time
from google import genai
from google.genai import types
from logger import get_logger
from config import MAX_PALABRAS

log = get_logger("vertex")

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL_ID = os.environ.get("VERTEX_GEMINI_MODEL", "gemini-2.5-flash-lite")

# "lectura" necesita mucho mas margen que "entorno"/"obstaculos": puede
# tener que transcribir un texto largo (una pagina de libro, un menu
# completo), y limitarlo al mismo tope de MAX_PALABRAS (pensado para
# respuestas cortas de uso diario) cortaria la transcripcion a la mitad.
# Los otros dos modos siguen usando MAX_PALABRAS (config.NIVEL_DETALLE,
# editable en la web) porque ahi la brevedad es una ventaja real. Este,
# en cambio, es un numero de tuning fijo (no cambia con nivel_detalle) --
# mismo criterio que RETENCION_DIAS: vive en .env con default de respaldo.
MAX_PALABRAS_LECTURA = int(os.environ.get("MAX_PALABRAS_LECTURA", "150"))

LIMITES_PALABRAS = {
    "entorno": MAX_PALABRAS,
    "lectura": MAX_PALABRAS_LECTURA,
    "obstaculos": MAX_PALABRAS,
}

# Margen ~3x sobre las palabras pedidas (mismo ratio que 40 palabras/120
# tokens, ya probado en produccion) para dejar lugar a tokens de puntuacion
# y variacion del modelo sin cortar la respuesta. Un tope de tokens propio
# por modo, calculado del mismo limite de palabras de arriba.
MAX_OUTPUT_TOKENS_POR_MODO = {
    modo: max(60, limite * 3) for modo, limite in LIMITES_PALABRAS.items()
}

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")

# Prompts por defecto -- respaldo si prompts/<modo>.txt falta, esta vacio,
# o tiene un error de formato. Mismo criterio anti-crash que config.py con
# config.json: contenido externo roto no debe tumbar el servicio. Deberian
# ser identicos a los .txt (si edita ahi, este respaldo queda desactualizado,
# pero solo se nota si el archivo real llega a fallar).
PROMPTS_DEFAULT = {
    "entorno": """
    Eres los ojos de una persona no vidente. Da contexto general de lo que la rodea en este momento: donde esta y que hay a su alrededor, de la forma mas precisa posible.

    Reglas:
    1. Describe el lugar y lo mas relevante: tipo de espacio, objetos, personas, superficies, y como estan ubicados entre si (izquierda/derecha/cerca/lejos). Se especifico: en vez de "una superficie" di que tipo (piso, mesa, pared). En vez de "un objeto", nombralo si lo reconoces.
    2. Prioriza precision sobre cantidad: si no estas seguro de algo, no lo inventes ni lo generalices de mas.
    3. Si hay texto visible (letrero, pantalla, libro), solo menciona que existe, sin transcribirlo palabra por palabra -- para leerlo completo esta el modo lectura.
    4. No evalues obstaculos ni distancias de transito -- para eso esta el modo obstaculos.
    5. Español latino directo, sin "hay", "veo", colores ni muletillas. Frases cortas, pero pueden ser 2-3 si hace falta para ser claro.
    6. Máximo {max_palabras} palabras.

    Ejemplos:
    "Cocina. Mesa al centro con frutas, una silla a cada lado."
    "Persona a tu derecha, con la mano levantada, parece saludar."
    "Sala amplia, sofá al frente, hay un letrero en la pared."
    "Un gato acostado en una silla de madera, a tu izquierda."
    """,

    "lectura": """
    Eres los ojos de una persona no vidente que quiere que le leas un texto. Tu trabajo es identificar de donde viene ese texto y transcribirlo literalmente.

    Reglas:
    1. Antes de transcribir, indica siempre en pocas palabras el tipo de fuente (ej. "Letrero:", "Libro:", "Etiqueta:", "Pantalla de celular:", "Documento:", "Menú:", "Envase:") para dar contexto de que esta leyendo.
    2. Despues transcribe el texto completo y textual -- no resumas, no parafrasees, no lo acortes.
    3. Si hay varios textos, lee primero el mas relevante o grande (titulo, encabezado), despues el resto, indicando la fuente de cada uno si cambia.
    4. No describas el resto de la escena, solo el texto y su fuente.
    5. Si no hay texto legible en la imagen, dilo claramente ("No se detecta texto para leer.") en vez de describir lo que se ve.
    6. Español latino directo, sin muletillas.
    7. Máximo {max_palabras} palabras (si el texto es mas largo, prioriza la parte mas relevante y dilo).

    Ejemplos:
    "Letrero: Prohibido estacionar."
    "Libro: Cien años de soledad, Gabriel García Márquez."
    "Pantalla de celular: 3 notificaciones nuevas de WhatsApp."
    "No se detecta texto para leer."
    """,

    "obstaculos": """
    Eres los ojos de una persona no vidente que necesita saber que hay en su camino inmediato para no chocar. Tu prioridad absoluta es identificar obstaculos y peligros cercanos, con su ubicacion y que tan cerca estan.

    Reglas:
    1. Menciona primero el obstaculo mas cercano o peligroso, solo si existe uno real y evidente en la imagen: que es, en que direccion (izquierda/derecha/frente) y que tan cerca esta (muy cerca, cerca, a distancia media, lejos).
    2. Si te doy una referencia de distancia del autoenfoque, es un dato de apoyo que puede no ser confiable -- usala UNICAMENTE si coincide con un obstaculo real que ya identificaste cerca de la camara, para afinar que tan cerca esta (traducila a las categorias de la regla 1, no repitas el numero exacto). Si la camara enfoco algo irrelevante (cielo, nubes, pared lejana, espacio abierto) o no hay ningun obstaculo cercano evidente, ignora esa referencia por completo -- no la menciones ni la uses.
    3. No inventes una distancia si no es evidente a partir de la imagen: es mejor decir "a distancia media" o no mencionar distancia, que arriesgar un dato incorrecto.
    4. Si hay varios obstaculos relevantes, ordenalos del mas cercano al mas lejano.
    5. No describas el ambiente general ni leas texto -- solo lo que puede interponerse en el paso.
    6. Si el camino esta despejado, dilo claramente ("Camino libre, no se detectan obstáculos a la vista.").
    7. Español latino directo, sin "hay", "veo", colores ni muletillas. Urgente si el peligro es inminente.
    8. Máximo {max_palabras} palabras.

    Ejemplos:
    "Silla muy cerca, al frente. Cuidado."
    "Escalera bajando al frente. Cuidado."
    "Mesa a distancia media, a tu izquierda. Camino libre a la derecha."
    "Camino libre, no se detectan obstáculos a la vista."
    """,
}

# dedent(): los triple-quoted de arriba heredan la indentacion del dict
# donde estan escritos (4 espacios por linea) -- se saca aca para que el
# respaldo, si llega a usarse, quede identico a los .txt (sin indentacion
# de mas colandose en el prompt real que recibe Gemini).
PROMPTS_DEFAULT = {modo: textwrap.dedent(texto).strip() for modo, texto in PROMPTS_DEFAULT.items()}


def _prompt_para_modo(modo, max_palabras):
    """Lee prompts/<modo>.txt y resuelve su {max_palabras}. Si el archivo
    falta, esta vacio, o falla el formateo (ej. alguien dejo una llave
    "{" suelta al editarlo a mano), cae al prompt por defecto de arriba
    y loguea un warning -- nunca crashea el servicio por esto."""
    ruta = os.path.join(PROMPTS_DIR, f"{modo}.txt")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            plantilla = f.read().strip()
        if not plantilla:
            raise ValueError("archivo vacio")
        return plantilla.format(max_palabras=max_palabras)
    except Exception as e:
        log.warning(f"No se pudo cargar prompts/{modo}.txt ({e}), usando prompt por defecto")
        return PROMPTS_DEFAULT[modo].format(max_palabras=max_palabras)


# Un prompt por modo (ver config.MODOS_RESERVADOS para las frases que los
# disparan). Cada uno tiene un alcance acotado a proposito para no pisar
# a los otros dos modos -- ej. "entorno" no transcribe texto (eso es
# trabajo de "lectura"), "lectura" no describe la escena, "obstaculos" no
# hace ninguna de las dos, solo evalua que hay en el camino. El contenido
# real vive en prompts/<modo>.txt, no aca -- editar ese archivo alcanza,
# no hace falta tocar este modulo.
PROMPTS = {
    modo: _prompt_para_modo(modo, LIMITES_PALABRAS[modo])
    for modo in PROMPTS_DEFAULT
}


def _limpiar_texto_lectura(texto):
    """Post-procesa la transcripcion de modo lectura con regex, no con mas
    reglas de prompt -- probado en vivo que pedirle a Gemini que "no corte
    palabras con guion" o "lea de corrido" no es confiable (fallo 0 de 6
    veces en una prueba real). Dos pasos:
    1. Une palabras separadas por el guion de fin de linea del libro
       ("mo-\\nmento" -> "momento"), el patron tipografico estandar de
       hyphenation -- siempre "letra-salto de linea-letra".
    2. Colapsa cualquier otro salto de linea/espacio de mas a un solo
       espacio, para que el texto que llega a TTS sea un bloque de prosa
       corrida -- si quedan saltos de linea sueltos (uno por cada linea
       del libro, no solo entre parrafos), Cloud TTS los lee como pausas,
       generando cortes raros a mitad de oracion."""
    texto = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", texto)
    return " ".join(texto.split())


def describir_o_leer(path_img: str, cycle_id=None, modo: str = "entorno", distancia_m=None) -> str:
    instruccion_asistente = PROMPTS.get(modo, PROMPTS["entorno"])
    max_output_tokens = MAX_OUTPUT_TOKENS_POR_MODO.get(modo, MAX_OUTPUT_TOKENS_POR_MODO["entorno"])

    # La distancia (estimada por el autoenfoque de camara.py, ver ese
    # modulo) solo se usa en modo obstaculos -- entorno/lectura la ignoran
    # aunque llegue. Va como parte del mensaje del usuario, no del
    # system_instruction, porque cambia en cada foto.
    instruccion_usuario = "Analiza y describe según tus instrucciones."
    if modo == "obstaculos" and distancia_m is not None:
        instruccion_usuario += (
            f" Dato de apoyo, puede no ser confiable: el autoenfoque de la camara quedo a "
            f"aproximadamente {distancia_m} metros. Usalo solo si corresponde a un obstaculo real y "
            "cercano que ya identificaste en la imagen, segun la regla sobre esto. Si no aplica (nada "
            "relevante enfocado, cielo, espacio abierto, sin obstaculo cercano), ignoralo por completo."
        )

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
                instruccion_usuario,
            ],
            config=types.GenerateContentConfig(
                system_instruction=instruccion_asistente,
                temperature=0.0,
                max_output_tokens=max_output_tokens,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )

        dt = time.time() - t0
        texto_final = (resp.text or "").strip()
        if texto_final:
            if modo == "lectura":
                texto_final = _limpiar_texto_lectura(texto_final)
            sufijo_distancia = f", distancia_m={distancia_m}" if modo == "obstaculos" else ""
            log.info(f'[{cycle_id}] OK ({MODEL_ID}, modo={modo}{sufijo_distancia}, {dt:.2f}s): "{texto_final}"')
            return texto_final
        else:
            log.warning(f"[{cycle_id}] Respuesta vacia ({MODEL_ID}, modo={modo}, {dt:.2f}s)")
            return "No detecto nada claro."

    except Exception as e:
        log.error(f"[{cycle_id}] Fallo ({MODEL_ID}, modo={modo}, {time.time()-t0:.2f}s): {e}")
        return "Error de conexión con el sensor visual."
