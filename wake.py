import vosk
import sounddevice as sd
import json
import os
import time
import threading
import uuid
from datetime import datetime
from boton import ejecutar
import subprocess
from logger import get_logger
from config import FRASES_ACTIVACION as WAKE_PHRASES

log = get_logger("wake")

MODEL_PATH = "/home/pichiloor/Documents/vosk-model-small-es-0.42"
WAKE_SOUND = "/home/pichiloor/Documents/woke.mp3"
SLEEP_SOUND = "/home/pichiloor/Documents/sleep.mp3"

SAMPLE_RATE = 44100

# Vosk (KaldiRecognizer) acumula memoria de forma continua mientras
# procesa audio, incluso sin activaciones (~3.6MB/min medido). En vez
# de reiniciar todo el proceso (cortaria la escucha unos segundos), se
# recrea solo el objeto KaldiRecognizer cada cierto tiempo, reutilizando
# el mismo Model ya cargado. El stream de audio nunca se detiene.
RECOGNIZER_RESET_INTERVAL = 5 * 60  # segundos

is_busy = False
wake_detected = False

model = vosk.Model(MODEL_PATH)
rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)
# Protege `rec`: el callback de audio (hilo de PortAudio) lo lee/muta
# via AcceptWaveform()/Result(), y el loop principal lo reemplaza por
# uno nuevo cada RECOGNIZER_RESET_INTERVAL. Sin lock, un wake dicho
# justo en el momento del reemplazo podia perderse.
rec_lock = threading.Lock()
last_recognizer_reset = time.time()

log.info("Sistema listo. Esperando wake...")


def _precargar_modulos_pesados():
    """vertex_context_vision.py y tts_cloud.py crean sus clientes de
    Google (genai.Client, TextToSpeechClient) al importarse -- boton.py
    los importa recien dentro de ejecutar() para no gastar esa RAM si
    el servicio nunca llega a usarlos, pero eso significa que la
    PRIMERA activacion real paga el costo del import + conexion
    (~14s medido). Se precargan aca en un hilo de fondo apenas arranca
    el servicio, para que ese costo caiga durante el boot (nadie
    esperando) y no en la primera vez que alguien dice la wake word.
    Import es thread-safe: si una activacion real llega antes de que
    esto termine, simplemente espera a que este hilo lo complete."""
    try:
        import vertex_context_vision
        import tts_cloud
        log.info("Modulos de Vertex/TTS precargados en background")
    except Exception as e:
        log.warning(f"No se pudieron precargar Vertex/TTS: {e}")
        return

    try:
        from saludo import asegurar_saludo
        ruta_saludo = asegurar_saludo()
        if ruta_saludo:
            play_sound(ruta_saludo)
    except Exception as e:
        log.warning(f"No se pudo reproducir el saludo: {e}")


def play_sound(path):
    subprocess.Popen(["mpg123", "-q", path])

def execute_boton(cycle_id):
    ejecutar(cycle_id)

def callback(indata, frames, time_info, status):
    global is_busy, wake_detected, rec

    if status:
        log.warning(f"Status de audio: {status}")

    if is_busy:
        return

    audio_bytes = bytes(indata)

    with rec_lock:
        if not rec.AcceptWaveform(audio_bytes):
            return
        result = json.loads(rec.Result())
    text = result.get("text", "").lower().strip()

    if not text:
        return

    log.info(f"Escuchado: {text}")

    for wake in WAKE_PHRASES:
        if wake in text:
            log.info("Wake detectado")
            is_busy = True
            wake_detected = True
            return

threading.Thread(target=_precargar_modulos_pesados, daemon=True).start()

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

            # ID de ciclo: se genera una sola vez por activacion y se usa
            # para nombrar la foto, el audio TTS, y etiquetar cada linea
            # de log de este ciclo -- asi se puede buscar ese ID y ver
            # todo lo relacionado (foto, respuesta de Vertex, audio) sin
            # tener que adivinar por cercania de horarios en el log.
            cycle_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]

            start_time = time.time()

            play_sound(WAKE_SOUND)

            log.info(f"[{cycle_id}] Ejecutando boton.py")
            execute_boton(cycle_id)

            play_sound(SLEEP_SOUND)

            log.info(f"[{cycle_id}] Tiempo total ciclo: {time.time() - start_time:.2f}s")

            with rec_lock:
                rec.Reset()
            time.sleep(1.0)

            log.info("Volviendo a esperar wake")
            is_busy = False
        else:
            if time.time() - last_recognizer_reset > RECOGNIZER_RESET_INTERVAL:
                nuevo_rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)
                with rec_lock:
                    rec = nuevo_rec
                last_recognizer_reset = time.time()
                log.info("KaldiRecognizer recreado (mantenimiento de memoria)")
            time.sleep(0.1)
