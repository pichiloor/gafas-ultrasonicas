#!/usr/bin/python3
import time
import os
from datetime import datetime
import subprocess

ruta_carpeta = "/home/pichiloor/Documents/capturas"
os.makedirs(ruta_carpeta, exist_ok=True)

def tomar_foto():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    archivo = f"{ruta_carpeta}/foto_{timestamp}.jpg"

    comando = [
        "rpicam-still",
	"--autofocus-on-capture",
	#"--af-mode", "continuous",
	"--width", "1280",
	"--height", "720",
        "-o", archivo,
        "--nopreview",
        "--timeout", "1200"
    ]

    try:
        subprocess.run(comando, check=True)
        print(f"Foto capturada: {archivo}")
        return archivo
    except Exception as e:
        print("Error al capturar:", e)
        return None
