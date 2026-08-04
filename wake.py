import vosk
import sounddevice as sd
import json
import os
import time
from boton import ejecutar
import subprocess

MODEL_PATH = "/home/pichiloor/Documents/vosk-model-small-es-0.42"
WAKE_SOUND = "/home/pichiloor/Documents/woke.mp3"
SLEEP_SOUND = "/home/pichiloor/Documents/sleep.mp3"

WAKE_PHRASES = [
    "hola gafas",
    "oye gafas",
    "hey gafas"
]

SAMPLE_RATE = 44100

# Vosk (KaldiRecognizer) acumula memoria de forma continua mientras
# procesa audio, incluso sin activaciones (~3.6MB/min medido en pruebas).
# En vez de reiniciar todo el proceso (lo que cortaria la escucha unos
# segundos cada vez), se recrea solo el objeto KaldiRecognizer cada
# cierto tiempo, reutilizando el mismo Model ya cargado. El stream de
# audio (RawInputStream) nunca se detiene, cero interrupcion real.
RECOGNIZER_RESET_INTERVAL = 15 * 60  # segundos

is_busy = False
wake_detected = False

model = vosk.Model(MODEL_PATH)
rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)
last_recognizer_reset = time.time()

print("Sistema listo. Esperando wake...")

# def play_sound(path):
#     os.system(f"mpg123 -q {path}")
def play_sound(path):
    subprocess.Popen(["mpg123", "-q", path])

def execute_boton():
    ejecutar()

def callback(indata, frames, time_info, status):
    global is_busy, wake_detected, rec

    if status:
        print(status)

    if is_busy:
        return

    audio_bytes = bytes(indata)

    if not rec.AcceptWaveform(audio_bytes):
        return

    result = json.loads(rec.Result())
    text = result.get("text", "").lower().strip()

    if not text:
        return

    print("Escuchado:", text)

    for wake in WAKE_PHRASES:
        if wake in text:
            print("Wake detectado")
            is_busy = True
            wake_detected = True
            return

with sd.RawInputStream(
    samplerate=SAMPLE_RATE,
    blocksize=8000,
    dtype="int16",
    channels=1,
    callback=callback
):
    while True:
        if wake_detected:
            wake_detected = False

            start_time = time.time()

            play_sound(WAKE_SOUND)

            #time.sleep(0.5)

            print("Ejecutando boton.py")
            execute_boton()

            play_sound(SLEEP_SOUND)

            print(f"Tiempo total ciclo: {time.time() - start_time:.2f}s")

            rec.Reset()
            time.sleep(1.0)

            print("Volviendo a esperar wake")
            is_busy = False
        else:
            if time.time() - last_recognizer_reset > RECOGNIZER_RESET_INTERVAL:
                rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)
                last_recognizer_reset = time.time()
                print("KaldiRecognizer recreado (mantenimiento de memoria)")
            time.sleep(0.1)
