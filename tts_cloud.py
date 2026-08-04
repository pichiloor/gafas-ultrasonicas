#!/usr/bin/python3
from google.cloud import texttospeech
import subprocess

# Cliente TTS persistente: se crea una sola vez al importar este modulo
# (cuando arranca wake.py) en vez de recrearlo en cada llamada a hablar().
# Crear el cliente toma ~1-1.3s (init de auth/canal); reutilizarlo ahorra
# ese tiempo en cada interaccion. Mismo patron que la camara persistente
# y el cliente de Vertex (vertex_context_vision.py).
client = texttospeech.TextToSpeechClient()

# Configuracion de voz (no cambia entre llamadas, se arma una sola vez)
voice = texttospeech.VoiceSelectionParams(
    language_code="es-US",
    name="es-US-Chirp3-HD-Aoede"   # Voz femenina, latina neutral
)

# Configuracion de salida MP3
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
)

def hablar(texto):
    # Limpieza del texto
    texto = texto.strip()
    if len(texto) < 2:
        texto = "No se detecto texto."

    # Texto a convertir
    synthesis_input = texttospeech.SynthesisInput(text=texto)

    # Solicitud a Google
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    # Archivo temporal MP3
    filename = "/home/pichiloor/Documents/tts_output.mp3"
    with open(filename, "wb") as out:
        out.write(response.audio_content)

    # Reproducir con mpg123
    subprocess.run(["mpg123", filename])
