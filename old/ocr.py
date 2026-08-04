#!/usr/bin/python3
import pytesseract
from PIL import Image
#import os

# Ruta donde se guardan las fotos
#ruta_fotos = "/home/pichiloor/Documents/capturas"

# Obtener lista de archivos .jpg
#fotos = [f for f in os.listdir(ruta_fotos) if f.lower().endswith(".jpg")]

#if not fotos:
#    print("No se encontraron fotos en la carpeta.")
#    exit()

# Ordenar por fecha/hora del nombre del archivo
# y seleccionar el más reciente
#fotos.sort()
#ultima_foto = fotos[-1]

#ruta_completa = os.path.join(ruta_fotos, ultima_foto)
#print(f"Procesando última foto:\n{ruta_completa}")

# Abrir imagen
def extraer_texto(ruta_imagen):
    try:
        imagen = Image.open(ruta_imagen)
    except Exception as e:
        print("No se pudo abrir la imagen:", e)
    return ""

    # Ejecutar OCR en español
    texto = pytesseract.image_to_string(imagen, lang="spa")

    print("\n===== TEXTO DETECTADO =====\n")
    print(texto)
    print("===========================\n")

    return texto.strip()
