#!/usr/bin/python3
# archivo: /home/pichiloor/ocr_manual.py

import os
import subprocess
import cv2
import numpy as np
import pytesseract
from PIL import Image
from datetime import datetime

# PARA INDICAR AL USUARIO QUE SE EMPIEZA EL PROCESO
subprocess.run(["espeak", "-v", "es", "TOMANDO FOTO"])

# ==================== CONFIGURACION ====================
RUTA_CARPETA = "/home/pichiloor/Documents/capturas"
os.makedirs(RUTA_CARPETA, exist_ok=True)

# Configuracion OCR optimizada para español y carteles reales
CONFIG_OCR = "--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,:!?()[]/-+="
# =======================================================

def tomar_foto():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ruta_raw = f"{RUTA_CARPETA}/raw_{timestamp}.jpg"
    ruta_lista = f"{RUTA_CARPETA}/lista_{timestamp}.jpg"

    comando = [
        "rpicam-still",
        "--width", "1280", "--height", "720",
        "--autofocus-on-capture",
        #"--awbgains", "1.5,1.5",
        #"--gain", "8",                              # Crucial en baja luz
        #"--denoise", "cdn_off",                     # Lo hacemos mejor nosotros
        #"--metering", "centre",
        "--quality", "90",
        #"--immediate",
        "-o", ruta_raw,
        "--nopreview",
        "--timeout", "800"
    ]

    print("Tomando foto...")
    try:
        subprocess.run(comando, check=True, timeout=10)
        print("Foto tomada!")
        return ruta_raw, ruta_lista
    except Exception as e:
        print("Error al capturar:", e)
        return None, None

def procesar_y_ocr(ruta_raw, ruta_salida):
    img = cv2.imread(ruta_raw)
    if img is None:
        return None

    # Preprocesamiento brutal para condiciones reales
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=15)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    contrast = clahe.apply(denoised)
    binary = cv2.adaptiveThreshold(contrast, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 31, 12)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Resize optimo para Tesseract
    h, w = closed.shape
    nuevo_ancho = 1200
    escala = nuevo_ancho / w
    final = cv2.resize(closed, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC)

    cv2.imwrite(ruta_salida, final)  # Para depuracion
    return Image.fromarray(final)

def decir_texto(texto):
    texto = texto.strip()
    if len(texto) < 4:
        print("No se detecto texto legible.")
        subprocess.run(["espeak", "-v", "es-", "No hay texto"])
    else:
        print("\n" + "="*60)
        print("TEXTO DETECTADO:")
        print(texto)
        print("="*60 + "\n")
        # Voz clara y natural (instala pico2wave si no lo tienes: sudo apt install libttspico-utils)
        subprocess.run(["espeak", "-v", "es", texto])

# ================================================
# EJECUCION MANUAL DEL SCRIPT
# ================================================
if __name__ == "__main__":
    ruta_raw, ruta_lista = tomar_foto()
    if ruta_raw and os.path.exists(ruta_raw):
        imagen_ocr = procesar_y_ocr(ruta_raw, ruta_lista)
        if imagen_ocr:
            texto = pytesseract.image_to_string(imagen_ocr, lang='spa', config=CONFIG_OCR)
            decir_texto(texto)
        else:
            decir_texto("Error procesando la imagen")
    else:
        decir_texto("Error al tomar la foto")
