#!/usr/bin/python3

from camara import tomar_foto
from ocr_cloud import extraer_texto_cloud as extraer_texto
from tts_cloud import hablar
import os

#hablar("¡Tomando foto!")
def ejecutar():
    ruta = tomar_foto()

    if not ruta or not os.path.exists(ruta):
        hablar("No se pudo tomar la foto.")
        return

    texto = extraer_texto(ruta)

    if not texto:
        hablar("No hay texto.")
    else:
        hablar(texto)

if __name__ == "__main__":
    ejecutar()
