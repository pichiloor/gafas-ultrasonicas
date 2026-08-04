#!/usr/bin/python3

import subprocess
import time

def hablar(texto):
    texto = texto.strip()
    if len(texto) < 2:
        texto = "No se detecto texto."

    print(texto)

    # Pausa corta para evitar cortes
    time.sleep(0.3)

    # Ejecutar espeak con velocidad reducida y tono mas natural
    comando = [
        "espeak",
        "-v", "es-la",   # voz en espanol latino
        "-s", "150",     # velocidad lenta (default 175)
        #"-p", "70",      # tono mas bajo y natural
        #"-k", "20",
        #"-a", "200",
        texto
    ]

    subprocess.run(comando)
