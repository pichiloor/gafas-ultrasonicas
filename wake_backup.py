import vosk
import sounddevice as sd
import json
import subprocess
import os

# Path to the Vosk Spanish small model
MODEL_PATH = "/home/pichiloor/Documents/vosk-model-small-es-0.42"

# Wake phrases
WAKE_PHRASES = ["hola gafas", "oye gafas", "hey gafas", "hello gafas"]

# Command phrases
COMMAND_PHRASES = ["que veo", "que hay", "camara", "foto", "¿que veo?", "¿que hay?", "toma foto", "tomar foto", "capturar"]

WAKE_SOUND = "/home/pichiloor/Documents/woke.mp3"

# Load model
model = vosk.Model(MODEL_PATH)
rec = vosk.KaldiRecognizer(model, 16000)

listening_for_command = False

print("System ready, waiting for wake phrase")

def reproducir_wake():
    os.system(f"mpg123 -q {WAKE_SOUND}")

def callback(indata, frames, time, status):
    global listening_for_command

    if rec.AcceptWaveform(bytes(indata)):
        result = json.loads(rec.Result())
        text = result.get("text", "").lower()

        if not text:
            return

        print("Heard:", text)

        # Wake detection
        if not listening_for_command:
            for wake in WAKE_PHRASES:
                if wake in text:
                    print("Wake detected")
                    reproducir_wake()
                    listening_for_command = True
                    return

        # Command detection
        if listening_for_command:
            for cmd in COMMAND_PHRASES:
                if cmd in text:
                    print("Command detected, running boton.py")
                    subprocess.call(["python3", "/home/pichiloor/Documents/boton.py"])
                    listening_for_command = False
                    return

            # Reset if no command matched
            listening_for_command = False
            print("Command not recognized")

# Start microphone stream
with sd.RawInputStream(
    samplerate=16000,
    blocksize=8000,
    dtype="int16",
    channels=1,
    callback=callback
):
    print("Listening...")
    while True:
        pass
