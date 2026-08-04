import cv2
import pytesseract
import numpy as np

LANG = "spa"
CUSTOM_CONFIG = r'--oem 3 --psm 6'

def deskew_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)

    coords = cv2.findNonZero(gray)
    if coords is None:
        return img

    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    if abs(angle) < 0.5:
        return img

    (h, w) = img.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    rot = cv2.warpAffine(img, M, (w, h),
                         flags=cv2.INTER_CUBIC,
                         borderMode=cv2.BORDER_REPLICATE)
    return rot


def preprocess_variants(img):
    img = cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    den = cv2.fastNlMeansDenoising(gray, h=10)

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    cla = clahe.apply(den)

    th1 = cv2.adaptiveThreshold(cla, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                cv2.THRESH_BINARY, 31, 10)

    _, th2 = cv2.threshold(cla, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
    th3 = cv2.morphologyEx(th2, cv2.MORPH_CLOSE, kernel, iterations=1)

    return [th1, th2, th3]


def extraer_texto(ruta_imagen):
    """Devuelve el texto mas confiable posible usando tres versiones de preprocesado"""

    img = cv2.imread(ruta_imagen)

    if img is None:
        return ""

    img = deskew_image(img)

    variantes = preprocess_variants(img)

    mejor = ""
    mejor_len = 0

    for v in variantes:
        texto = pytesseract.image_to_string(v, lang=LANG, config=CUSTOM_CONFIG)
        clean = texto.strip()

        if len(clean) > mejor_len:
            mejor_len = len(clean)
            mejor = clean

    return mejor
