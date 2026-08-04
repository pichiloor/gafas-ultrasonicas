#!/usr/bin/python3
from google.cloud import texttospeech
import subprocess

def hablar(texto):
    # Limpieza del texto
    texto = texto.strip()
    if len(texto) < 2:
        texto = "No se detecto texto."

    # Crear cliente Google TTS
    client = texttospeech.TextToSpeechClient()

    # Texto a convertir
    synthesis_input = texttospeech.SynthesisInput(text=texto)

    # Configuracion de voz
    voice = texttospeech.VoiceSelectionParams(
        language_code="es-ES",
        name="es-ES-Standard-A"   # Voz femenina estandar
    )

    # Configuracion de salida MP3
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

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
