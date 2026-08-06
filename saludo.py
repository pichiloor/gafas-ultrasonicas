#!/usr/bin/python3
"""
Genera y cachea el audio del saludo de bienvenida ("¡Hola, {nombre}!").
Se regenera solo cuando cambia algo que afecta el resultado (nombre,
texto del saludo, o voz) -- se guarda un hash de esos valores junto al
mp3, asi un reinicio normal no vuelve a golpear la API de TTS si nada
cambio en config.json.

La velocidad del saludo es fija (VELOCIDAD_SALUDO), independiente de
velocidad_habla (que aplica a las descripciones). Se eligio 0.7 tras
comparar varias opciones al oido -- a 1.0 sonaba plano/poco amigable;
0.7 + la coma en el texto ("Hola," en vez de "Hola") fue lo que sono
mas calido.
"""
import os
import hashlib
from logger import get_logger
from config import NOMBRE_USUARIO, SALUDO, GENERO_VOZ
from tts_cloud import client, voice
from google.cloud import texttospeech

log = get_logger("saludo")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SALUDO_MP3 = os.path.join(BASE_DIR, "saludo.mp3")
SALUDO_HASH = os.path.join(BASE_DIR, "saludo.hash")

VELOCIDAD_SALUDO = 0.7

_audio_config_saludo = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3,
    speaking_rate=VELOCIDAD_SALUDO,
)


def _texto_saludo() -> str:
    try:
        return SALUDO.format(nombre=NOMBRE_USUARIO)
    except Exception as e:
        # template invalido (ej. placeholder mal escrito desde una futura
        # web) -- no crashear, se usa el texto tal cual quedo.
        log.warning(f"Saludo con formato invalido ({e}), se usa el texto sin reemplazar")
        return SALUDO


def _hash_actual() -> str:
    firma = f"{NOMBRE_USUARIO}|{SALUDO}|{GENERO_VOZ}|{VELOCIDAD_SALUDO}"
    return hashlib.sha256(firma.encode("utf-8")).hexdigest()


def _hash_guardado():
    if not os.path.exists(SALUDO_HASH):
        return None
    try:
        with open(SALUDO_HASH, "r") as f:
            return f.read().strip()
    except Exception:
        return None


def asegurar_saludo():
    """Devuelve la ruta al mp3 del saludo, regenerandolo si cambio algo
    relevante de la config desde la ultima vez. None si nunca se pudo
    generar (ej. sin conexion) y tampoco hay uno cacheado para reusar."""
    hash_actual = _hash_actual()

    if hash_actual == _hash_guardado() and os.path.exists(SALUDO_MP3):
        log.info("Saludo sin cambios, se reusa el audio cacheado")
        return SALUDO_MP3

    texto = _texto_saludo()
    try:
        synthesis_input = texttospeech.SynthesisInput(text=texto)
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=_audio_config_saludo,
        )
        with open(SALUDO_MP3, "wb") as f:
            f.write(response.audio_content)
        with open(SALUDO_HASH, "w") as f:
            f.write(hash_actual)
        log.info(f'Saludo regenerado: "{texto}" (velocidad={VELOCIDAD_SALUDO})')
        return SALUDO_MP3
    except Exception as e:
        log.error(f"No se pudo generar el saludo ({e})")
        return SALUDO_MP3 if os.path.exists(SALUDO_MP3) else None
