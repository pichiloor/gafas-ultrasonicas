#!/usr/bin/python3
import os
import subprocess
import time
from logger import get_logger, carpeta_del_dia, nombre_archivo

log = get_logger("camara")

# Sin cámara persistente ni estado global: cada foto abre la cámara,
# enfoca y cierra en un subproceso aislado. Más lento que mantenerla
# abierta (el autoenfoque físico del IMX519 tarda lo que tarda, no hay
# forma de evitarlo) pero simple y sin superficie de bugs -- nada que
# pueda quedar en None, ni estado que se corrompa entre llamadas, ni
# proceso que compita por el dispositivo con nada mas.
COMANDO_BASE = [
    "rpicam-still",
    "--autofocus-on-capture",
    "--width", "1280",
    "--height", "720",
    "--nopreview",
    "--timeout", "1200",
]


def tomar_foto(cycle_id=None):
    carpeta_dia = carpeta_del_dia()
    nombre = nombre_archivo(cycle_id)
    archivo = os.path.join(carpeta_dia, f"{nombre}.jpg")

    comando = COMANDO_BASE + ["-o", archivo]

    t0 = time.time()
    try:
        subprocess.run(comando, check=True, capture_output=True, text=True)
        log.info(f"[{cycle_id}] Foto capturada: {archivo} ({time.time()-t0:.2f}s)")
        return archivo
    except subprocess.CalledProcessError as e:
        log.error(f"[{cycle_id}] Error al capturar foto: {e.stderr.strip()}")
        return None
    except Exception as e:
        log.error(f"[{cycle_id}] Error al capturar foto: {e}")
        return None
