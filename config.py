#!/usr/bin/python3
"""
Config editable del asistente (nombre, saludo, voz, frases de activacion,
nivel de detalle de la descripcion). Lee config.json junto a este archivo;
si falta o esta mal formado, cae en valores por defecto sin tumbar el resto
del sistema (mismo criterio que camara.py/logger.py: una config secundaria
nunca debe crashear el flujo principal).
"""
import json
import os
import unicodedata
from logger import get_logger

log = get_logger("config")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# Voces Chirp3-HD disponibles en es-US, confirmadas via list_voices() (2026-08-05).
VOCES = {
    "femenino": "es-US-Chirp3-HD-Aoede",
    "masculino": "es-US-Chirp3-HD-Puck",
}

MAX_FRASES_ACTIVACION = 5

# Palabras reservadas para cambiar de modo -- cada modo puede tener mas de
# una frase (variaciones/sinonimos), por eso es una lista, igual que
# frases_activacion. A diferencia de frases_activacion (que el usuario
# edita libremente desde la web y solo sirven de "ping" para confirmar que
# el sistema escucha), estas son fijas en el codigo: no se guardan en
# config.json y no se pueden editar desde la web. Para agregar una
# variacion nueva (ej. "gafas, que hay" como sinonimo de obstaculos) alcanza
# con sumarla a la lista del modo correspondiente aca abajo.
MODOS_RESERVADOS = {
    "entorno": ["gafas, entorno"],
    "lectura": ["gafas, lectura", "gafas, leer", "gafas, texto", "gafas, lee"],
    "obstaculos": ["gafas, obstáculos", "gafas, obstáculo", "gafas, peligro"],
}

# Una linea explicando que hace cada modo -- se muestra en el panel web
# junto a sus frases, para que se entienda la diferencia entre los tres.
DESCRIPCIONES_MODOS = {
    "entorno": "Describe el lugar en general: qué hay, quién hay, cómo está todo ubicado.",
    "lectura": "Lee en voz alta cualquier texto que encuentre (letreros, libros, etiquetas).",
    "obstaculos": "Avisa qué obstáculos hay cerca y en qué dirección, para caminar seguro.",
}


def normalizar(texto: str) -> str:
    """minusculas, sin tildes, sin comas -- para comparar lo que Vosk
    transcribe contra las frases fijas/configurables sin que un acento o
    signo de puntuacion cambie el resultado del match."""
    texto = texto.lower().strip()
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(sin_tildes.replace(",", " ").split())


# Version normalizada de MODOS_RESERVADOS (una lista de frases normalizadas
# por modo), lista para comparar contra texto ya normalizado -- usada por
# wake.py y para filtrar colisiones aqui abajo.
FRASES_MODOS_NORMALIZADAS = {
    modo: [normalizar(frase) for frase in frases]
    for modo, frases in MODOS_RESERVADOS.items()
}

# Todas las frases reservadas juntas en una sola lista plana (sin agrupar
# por modo) -- util para chequeos de colision donde no importa a que modo
# pertenece cada una, solo si esta reservada.
FRASES_RESERVADAS_NORMALIZADAS = {
    f for frases in FRASES_MODOS_NORMALIZADAS.values() for f in frases
}

# Palabras maximas de la descripcion de Vertex segun nivel elegido.
# "detallado" (40) es el default historico ya probado; "breve" (20) era
# el limite original antes de que se ampliara para dar mejores descripciones.
NIVELES_DETALLE = {
    "breve": 20,
    "detallado": 40,
}

DEFAULTS = {
    "nombre_usuario": "Usuario",
    "saludo": "Hola {nombre}!",
    "velocidad_habla": 1.0,
    "genero_voz": "femenino",
    "frases_activacion": ["hola gafas", "oye gafas", "hey gafas"],
    "nivel_detalle": "detallado",
}


def _validar(cfg: dict) -> dict:
    validado = DEFAULTS.copy()

    nombre = cfg.get("nombre_usuario")
    if isinstance(nombre, str) and nombre.strip():
        validado["nombre_usuario"] = nombre.strip()
    elif nombre is not None:
        log.warning(f"nombre_usuario invalido ({nombre!r}), usando default")

    saludo = cfg.get("saludo")
    if isinstance(saludo, str):
        validado["saludo"] = saludo
    elif saludo is not None:
        log.warning(f"saludo invalido ({saludo!r}), usando default")

    velocidad = cfg.get("velocidad_habla")
    if isinstance(velocidad, (int, float)) and not isinstance(velocidad, bool) and 0.5 <= velocidad <= 2.0:
        validado["velocidad_habla"] = float(velocidad)
    elif velocidad is not None:
        log.warning(f"velocidad_habla invalida ({velocidad!r}, debe estar entre 0.5 y 2.0), usando default {DEFAULTS['velocidad_habla']}")

    genero = cfg.get("genero_voz")
    if genero in VOCES:
        validado["genero_voz"] = genero
    elif genero is not None:
        log.warning(f"genero_voz invalido ({genero!r}, opciones: {list(VOCES)}), usando default {DEFAULTS['genero_voz']}")

    frases = cfg.get("frases_activacion")
    if isinstance(frases, list):
        limpias = [f.strip().lower() for f in frases if isinstance(f, str) and f.strip()]

        antes = len(limpias)
        limpias = [f for f in limpias if normalizar(f) not in FRASES_RESERVADAS_NORMALIZADAS]
        if len(limpias) < antes:
            todas_reservadas = [f for frases in MODOS_RESERVADOS.values() for f in frases]
            log.warning(
                "Se descartaron frases_activacion que chocaban con palabras "
                f"reservadas de modo ({sorted(todas_reservadas)})"
            )

        if limpias:
            if len(limpias) > MAX_FRASES_ACTIVACION:
                log.warning(f"frases_activacion tiene {len(limpias)} frases, se recorta a las primeras {MAX_FRASES_ACTIVACION}")
                limpias = limpias[:MAX_FRASES_ACTIVACION]
            validado["frases_activacion"] = limpias
        else:
            log.warning("frases_activacion vacia o sin frases validas, usando default")
    elif frases is not None:
        log.warning(f"frases_activacion invalida ({frases!r}, debe ser una lista de texto), usando default")

    nivel = cfg.get("nivel_detalle")
    if nivel in NIVELES_DETALLE:
        validado["nivel_detalle"] = nivel
    elif nivel is not None:
        log.warning(f"nivel_detalle invalido ({nivel!r}, opciones: {list(NIVELES_DETALLE)}), usando default {DEFAULTS['nivel_detalle']}")

    return validado


def cargar_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        log.warning(f"No existe {CONFIG_PATH}, usando valores por defecto")
        return DEFAULTS.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        log.error(f"No se pudo leer/parsear config.json ({e}), usando valores por defecto")
        return DEFAULTS.copy()
    return _validar(cfg)


CONFIG = cargar_config()
NOMBRE_USUARIO = CONFIG["nombre_usuario"]
SALUDO = CONFIG["saludo"]
VELOCIDAD_HABLA = CONFIG["velocidad_habla"]
GENERO_VOZ = CONFIG["genero_voz"]
VOZ_NOMBRE = VOCES[GENERO_VOZ]
FRASES_ACTIVACION = CONFIG["frases_activacion"]
NIVEL_DETALLE = CONFIG["nivel_detalle"]
MAX_PALABRAS = NIVELES_DETALLE[NIVEL_DETALLE]

log.info(
    f"Config cargada: nombre={NOMBRE_USUARIO!r}, velocidad={VELOCIDAD_HABLA}, "
    f"voz={GENERO_VOZ} ({VOZ_NOMBRE}), frases_activacion={FRASES_ACTIVACION} (ping), "
    f"modos_reservados={MODOS_RESERVADOS}, "
    f"nivel_detalle={NIVEL_DETALLE} (max_palabras={MAX_PALABRAS})"
)
