#!/usr/bin/python3
import os
import time
from google.cloud import texttospeech
import subprocess
from logger import get_logger, carpeta_del_dia, nombre_archivo

log = get_logger("tts")

# Cliente TTS persistente: se crea una sola vez al importar este modulo
# en vez de recrearlo en cada llamada a hablar().
client = texttospeech.TextToSpeechClient()

voice = texttospeech.VoiceSelectionParams(
    language_code="es-US",
    name="es-US-Chirp3-HD-Aoede"   # Voz femenina, latina neutral
)

audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
)


def hablar(texto, cycle_id=None):
    texto = texto.strip()
    if len(texto) < 2:
        texto = "No se detecto texto."

    synthesis_input = texttospeech.SynthesisInput(text=texto)

    t0 = time.time()
    try:
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
    except Exception as e:
        log.error(f'[{cycle_id}] Fallo TTS: {e} -- texto: "{texto}"')
        return

    carpeta_dia = carpeta_del_dia()
    nombre = nombre_archivo(cycle_id)
    filename = os.path.join(carpeta_dia, f"{nombre}.mp3")

    with open(filename, "wb") as out:
        out.write(response.audio_content)

    log.info(f'[{cycle_id}] OK ({time.time()-t0:.2f}s): "{texto}" -> {filename}')

    subprocess.run(["mpg123", filename])
