#!/usr/bin/python3
"""
Modulo central de logging para gafas-ultrasonicas.
Escribe a ~/Documents/logs/YYYY/MM/DD/YYYY-MM-DD.log -- el log del dia
vive junto con las fotos y audios de ese mismo dia, todo en una sola
carpeta (año/mes/dia, sin repetir formato entre niveles). Tambien manda
todo a stdout (asi journalctl/systemctl status siguen mostrando las
mismas lineas que antes).
"""
import logging
import os
from datetime import datetime

BASE_DIR = "/home/pichiloor/Documents"
LOGS_DIR = os.path.join(BASE_DIR, "logs")


def carpeta_del_dia(fecha=None):
    fecha = fecha or datetime.now()
    carpeta = os.path.join(
        LOGS_DIR,
        fecha.strftime("%Y"),
        fecha.strftime("%m"),
        fecha.strftime("%d"),
    )
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


class DailyFileHandler(logging.Handler):
    """Escribe al archivo del dia actual; cambia de archivo solo si
    cambia la fecha, sin necesidad de reiniciar el proceso."""

    def __init__(self):
        super().__init__()
        self._current_date = None
        self._file = None

    def _path_for_today(self):
        now = datetime.now()
        carpeta = carpeta_del_dia(now)
        return os.path.join(carpeta, now.strftime("%Y-%m-%d") + ".log")

    def emit(self, record):
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._current_date:
            if self._file:
                self._file.close()
            self._file = open(self._path_for_today(), "a", encoding="utf-8")
            self._current_date = today
        try:
            self._file.write(self.format(record) + "\n")
            self._file.flush()
        except Exception:
            pass


_configured = set()


def get_logger(nombre):
    logger = logging.getLogger(nombre)
    if nombre in _configured:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = DailyFileHandler()
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    logger.addHandler(stream_handler)

    logger.propagate = False
    _configured.add(nombre)
    return logger
