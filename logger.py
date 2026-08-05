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


def nombre_archivo(cycle_id=None):
    """Nombre base (sin extension) para la foto/audio de un ciclo.
    Usa el cycle_id si viene dado (compartido entre foto y audio TTS
    del mismo ciclo); si no, cae a un prefijo 'test_' + horario propio
    para distinguir corridas manuales/pruebas en los logs."""
    return cycle_id if cycle_id else "test_" + datetime.now().strftime("%Y%m%d-%H%M%S")


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
        # Todo el rotado (incluido el open() del archivo nuevo) va
        # protegido: si falla -- SD en solo-lectura, permisos, ruta
        # borrada -- se descarta la linea en vez de tumbar al que
        # esta logueando. El archivo viejo solo se cierra despues de
        # abrir el nuevo con exito, para no perder el fd si el open
        # nuevo falla.
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            if today != self._current_date:
                nuevo_archivo = open(self._path_for_today(), "a", encoding="utf-8")
                if self._file:
                    self._file.close()
                self._file = nuevo_archivo
                self._current_date = today
            self._file.write(self.format(record) + "\n")
            self._file.flush()
        except Exception:
            pass


_configured = set()

_fmt = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Un unico DailyFileHandler compartido por todos los loggers del
# proceso (wake, boton, camara, tts, vertex): todos escriben al mismo
# archivo del dia, asi que comparten un solo file descriptor en vez de
# uno cada uno.
_file_handler = DailyFileHandler()
_file_handler.setFormatter(_fmt)


def get_logger(nombre):
    logger = logging.getLogger(nombre)
    if nombre in _configured:
        return logger
    logger.setLevel(logging.INFO)

    logger.addHandler(_file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(_fmt)
    logger.addHandler(stream_handler)

    logger.propagate = False
    _configured.add(nombre)
    return logger
