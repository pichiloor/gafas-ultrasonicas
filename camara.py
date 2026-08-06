#!/usr/bin/python3
import json
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

# Metadata de la captura (incluye LensPosition) se pide siempre -- medido
# en vivo que no agrega latencia (~2.6-2.7s con o sin metadata, dentro del
# ruido normal). Un solo path fijo porque tomar_foto() nunca se llama en
# paralelo (loop principal de wake.py es secuencial), se pisa en cada
# ciclo sin falta.
METADATA_TMP = "/tmp/gafas_metadata.json"


def _distancia_desde_metadata(ruta_metadata, cycle_id=None):
    """Estima la distancia al objeto donde enfoco la camara a partir del
    LensPosition (dioptrias = 1/metros) que reporta el autoenfoque del
    IMX519 en los metadatos de la captura. Es una referencia aproximada
    de UN solo punto -- el que la camara eligio enfocar (normalmente el
    sujeto dominante/central del cuadro), no mide el resto de la imagen.
    No calibrado contra distancias reales conocidas todavia -- revisar
    los logs (quedan lens_position + metros juntos) si hace falta ajustar
    la formula mas adelante. Nunca rompe la captura de foto por esto:
    cualquier fallo devuelve None y sigue."""
    try:
        with open(ruta_metadata) as f:
            metadata = json.load(f)
        dioptrias = metadata.get("LensPosition")
        if not dioptrias or dioptrias <= 0:
            return None
        metros = round(1 / dioptrias, 2)
        log.info(f"[{cycle_id}] Distancia estimada por autoenfoque: {metros}m (lens_position={dioptrias:.3f})")
        return metros
    except Exception as e:
        log.warning(f"[{cycle_id}] No se pudo estimar distancia por autoenfoque: {e}")
        return None


def tomar_foto(cycle_id=None):
    """Devuelve (ruta_archivo, distancia_m). distancia_m es None si no se
    pudo estimar (no es motivo de error -- la foto en si se toma igual)."""
    carpeta_dia = carpeta_del_dia()
    nombre = nombre_archivo(cycle_id)
    archivo = os.path.join(carpeta_dia, f"{nombre}.jpg")

    comando = COMANDO_BASE + [
        "-o", archivo,
        "--metadata", METADATA_TMP,
        "--metadata-format", "json",
    ]

    t0 = time.time()
    try:
        subprocess.run(comando, check=True, capture_output=True, text=True)
        log.info(f"[{cycle_id}] Foto capturada: {archivo} ({time.time()-t0:.2f}s)")
        distancia_m = _distancia_desde_metadata(METADATA_TMP, cycle_id)
        return archivo, distancia_m
    except subprocess.CalledProcessError as e:
        log.error(f"[{cycle_id}] Error al capturar foto: {e.stderr.strip()}")
        return None, None
    except Exception as e:
        log.error(f"[{cycle_id}] Error al capturar foto: {e}")
        return None, None
