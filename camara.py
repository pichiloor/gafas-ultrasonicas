#!/usr/bin/python3
import os
from datetime import datetime
from picamera2 import Picamera2
from libcamera import controls

ruta_carpeta = "/home/pichiloor/Documents/capturas"
os.makedirs(ruta_carpeta, exist_ok=True)

# Camara persistente: se abre una sola vez al importar este modulo
# (cuando arranca wake.py como servicio) y queda con autoenfoque
# continuo corriendo de fondo mientras el sistema espera la palabra
# de activacion. Asi, cuando se pide una foto, el lente ya esta
# enfocado y la captura es casi instantanea.
# Antes: rpicam-still arrancaba la camara desde cero en cada foto y
# el autoenfoque agregaba ~6-7s por captura.
picam2 = Picamera2()
_config = picam2.create_still_configuration(main={"size": (1280, 720)})
picam2.configure(_config)
picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
picam2.start()

def tomar_foto():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    archivo = f"{ruta_carpeta}/foto_{timestamp}.jpg"

    try:
        picam2.capture_file(archivo)
        print(f"Foto capturada: {archivo}")
        return archivo
    except Exception as e:
        print("Error al capturar:", e)
        return None
