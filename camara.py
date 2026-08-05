#!/usr/bin/python3
import os
import time
from datetime import datetime
from picamera2 import Picamera2
from libcamera import controls
from logger import get_logger, carpeta_del_dia

log = get_logger("camara")

# Camara persistente: se abre una sola vez al importar este modulo
# (cuando arranca wake.py) y queda con autoenfoque continuo corriendo
# de fondo mientras el sistema espera la palabra de activacion.
picam2 = Picamera2()
_config = picam2.create_still_configuration(main={"size": (1280, 720)})
picam2.configure(_config)
picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
picam2.start()


def tomar_foto(cycle_id=None):
    carpeta_dia = carpeta_del_dia()
    # Usa el cycle_id (compartido con el audio TTS del mismo ciclo) si
    # viene dado; si no, cae al horario propio (uso manual/pruebas).
    nombre = cycle_id if cycle_id else "test_" + datetime.now().strftime("%Y%m%d-%H%M%S")
    archivo = os.path.join(carpeta_dia, f"{nombre}.jpg")

    t0 = time.time()
    try:
        picam2.capture_file(archivo)
        log.info(f"[{cycle_id}] Foto capturada: {archivo} ({time.time()-t0:.2f}s)")
        return archivo
    except Exception as e:
        log.error(f"[{cycle_id}] Error al capturar foto: {e}")
        return None
