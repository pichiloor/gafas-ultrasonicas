#!/usr/bin/python3
from ocr_cloud import extraer_texto_cloud

ruta = "/home/pichiloor/Documents/capturas/foto_2025-12-12_11-39-04.jpg"

texto = extraer_texto_cloud(ruta)

print("===== TEXTO DETECTADO =====")
print(texto)
print("===========================")
