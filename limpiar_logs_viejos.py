#!/usr/bin/python3
"""
Borra carpetas de dia (fotos + audio + log juntos) mas viejas que
RETENCION_DIAS (variable de entorno, configurable en .env; default 180
si no esta seteada). Corre una vez al iniciar el sistema (la Pi no
queda prendida todo el tiempo, asi que un timer de calendario diario se
puede perder arranques seguidos sin encender la maquina a esa hora).
"""
import os
import re
import shutil
from datetime import datetime, timedelta

RETENCION_DIAS = int(os.environ.get("RETENCION_DIAS", "180"))

LOGS_DIR = "/home/pichiloor/Documents/logs"

limite = datetime.now() - timedelta(days=RETENCION_DIAS)
borrados = 0

if os.path.isdir(LOGS_DIR):
    for year in os.listdir(LOGS_DIR):
        ruta_year = os.path.join(LOGS_DIR, year)
        if not os.path.isdir(ruta_year) or not re.match(r"^\d{4}$", year):
            continue
        for month in os.listdir(ruta_year):
            ruta_month = os.path.join(ruta_year, month)
            if not os.path.isdir(ruta_month) or not re.match(r"^\d{2}$", month):
                continue
            for day in os.listdir(ruta_month):
                ruta_day = os.path.join(ruta_month, day)
                if not os.path.isdir(ruta_day) or not re.match(r"^\d{2}$", day):
                    continue
                try:
                    fecha = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
                except ValueError:
                    continue
                if fecha < limite:
                    shutil.rmtree(ruta_day, ignore_errors=True)
                    print(f"Borrado: {ruta_day}")
                    borrados += 1
            if os.path.isdir(ruta_month) and not os.listdir(ruta_month):
                os.rmdir(ruta_month)
        if os.path.isdir(ruta_year) and not os.listdir(ruta_year):
            os.rmdir(ruta_year)

print(f"Limpieza terminada (retencion: {RETENCION_DIAS} dias, {borrados} carpetas borradas)")
