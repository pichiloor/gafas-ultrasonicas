#!/usr/bin/python3
import os
import time
from picamera2 import Picamera2
from libcamera import controls
from logger import get_logger, carpeta_del_dia, nombre_archivo

log = get_logger("camara")


def _iniciar_camara():
    """Abre y configura la camara. Si falla (p.ej. race de arranque o
    camara ocupada), devuelve None en vez de propagar la excepcion --
    un fallo aca no debe tumbar el import de wake.py/boton.py."""
    try:
        cam = Picamera2()
        config = cam.create_still_configuration(main={"size": (1280, 720)})
        cam.configure(config)
        cam.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        cam.start()
        return cam
    except Exception as e:
        log.error(f"Error al iniciar camara: {e}")
        return None


# Camara persistente: se abre una sola vez al importar este modulo
# (cuando arranca wake.py) y queda con autoenfoque continuo corriendo
# de fondo mientras el sistema espera la palabra de activacion. Si la
# camara no esta lista todavia, tomar_foto() reintenta el init bajo
# demanda en vez de dejar picam2 en None para siempre.
picam2 = _iniciar_camara()


def tomar_foto(cycle_id=None):
    global picam2

    if picam2 is None:
        picam2 = _iniciar_camara()
        if picam2 is None:
            log.error(f"[{cycle_id}] Camara no disponible, se omite la foto")
            return None

    carpeta_dia = carpeta_del_dia()
    nombre = nombre_archivo(cycle_id)
    archivo = os.path.join(carpeta_dia, f"{nombre}.jpg")

    t0 = time.time()
    try:
        picam2.capture_file(archivo)
        log.info(f"[{cycle_id}] Foto capturada: {archivo} ({time.time()-t0:.2f}s)")
        return archivo
    except Exception as e:
        log.error(f"[{cycle_id}] Error al capturar foto: {e}")
        return None
