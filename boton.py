#!/usr/bin/python3

from camara import tomar_foto
#from vision_mix_cloud import analizar_imagen_cloud as extraer_texto
import os
from diccionario import traducir
import subprocess
from logger import get_logger

log = get_logger("boton")

SHUTTER_SOUND = "/home/pichiloor/Documents/camera-shutter.mp3"

def play_sound(path):
    subprocess.Popen(["mpg123", "-q", path])

def ejecutar(cycle_id=None):
    # Imports diferidos: vertex_context_vision y tts_cloud cargan SDKs
    # pesados de Google. Se importan aqui (no al tope del modulo) para
    # que ese peso solo se cargue en RAM cuando de verdad se necesita.
    from vertex_context_vision import describir_o_leer
    from tts_cloud import hablar

    ruta = tomar_foto(cycle_id)

    if not ruta or not os.path.exists(ruta):
        log.error(f"[{cycle_id}] No se pudo tomar la foto")
        hablar("No se pudo tomar la foto.", cycle_id)
        return

    play_sound(SHUTTER_SOUND)

    mensaje = describir_o_leer(ruta, cycle_id)
    log.info(f"[{cycle_id}] Mensaje final: {mensaje}")
    hablar(mensaje, cycle_id)


if __name__ == "__main__":
    ejecutar()
