#!/usr/bin/python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import pytesseract
from PIL import Image

def extraer_texto(ruta):
    img = cv2.imread(ruta)
    if img is None:
        return ""

    # Convertir a escala de grises
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Reducir ruido
    denoise = cv2.fastNlMeansDenoising(gray, h=12)

    # Mejorar contraste
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoise)

    # Binarizacion fuerte para texto
    bw = cv2.adaptiveThreshold(
        enhanced, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 12
    )

    # Intento de corregir inclinacion sin obligar a usarlo
    try:
        coords = np.column_stack(np.where(bw > 0))
        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        (h, w) = bw.shape
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1)
        deskew = cv2.warpAffine(
            bw, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
    except:
        # Si falla la deteccion de angulo se usa la imagen normal
        deskew = bw

    # Agrandar la imagen para mejorar OCR
    enlarged = cv2.resize(deskew, None, fx=1.4, fy=1.4, interpolation=cv2.INTER_LINEAR)

    # Convertir a formato PIL
    pil_img = Image.fromarray(enlarged)

    # Leer texto con tesseract
    texto = pytesseract.image_to_string(pil_img, lang="spa")

    return texto.strip()
