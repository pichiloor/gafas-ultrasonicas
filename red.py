#!/usr/bin/python3
"""
Manejo de redes WiFi (via nmcli/NetworkManager) y estado de audio, para el
panel web.

Regla de seguridad dura, no negociable: NUNCA se modifica ni se elimina la
conexion actualmente activa (hoy "PICHILOOR", el hotspot del celular del
usuario) -- se chequea en vivo cual esta activa antes de cualquier operacion
destructiva, nunca se asume un nombre fijo (asi sigue protegida aunque el
usuario cambie de red principal en el futuro). Agregar una red nueva NUNCA
se conecta a ella ni toca la actual -- queda guardada con prioridad baja,
para que NetworkManager la use solo si ninguna red de mayor prioridad
(la principal incluida) esta disponible.

pichiloor no tiene permisos de NetworkManager para modificar conexiones sin
sudo (confirmado: `nmcli general permissions` devuelve "auth" para
network-control), pero tiene sudo sin password a nivel de sistema -- se usa
sudo solo en las operaciones que lo requieren (agregar/eliminar), nunca en
las de solo lectura (listar, escanear, ver estado de audio).
"""
import re
import subprocess
import time
from logger import get_logger

log = get_logger("red")

# Prioridad de una red recien agregada -- siempre por debajo de cualquier
# red ya configurada (la principal incluida, que hoy esta en 0), para que
# nunca compita con la conexion en uso.
PRIORIDAD_REDES_NUEVAS = -10


def _nmcli(args, usar_sudo=False):
    comando = (["sudo"] if usar_sudo else []) + ["nmcli"] + args
    try:
        return subprocess.run(comando, capture_output=True, text=True, timeout=20)
    except Exception as e:
        log.error(f"Fallo ejecutando nmcli {args}: {e}")
        return subprocess.CompletedProcess(comando, 1, "", str(e))


def _conexion_activa():
    """Nombre de la conexion wifi actualmente activa, o None. Se recalcula
    en cada llamada -- nunca se cachea, porque es justo lo que protege
    contra modificar o borrar la red en uso por accidente."""
    r = _nmcli(["-t", "-f", "NAME,TYPE,STATE", "connection", "show", "--active"])
    if r.returncode != 0:
        log.warning(f"No se pudo consultar conexion activa: {r.stderr.strip()}")
        return None
    for linea in r.stdout.strip().splitlines():
        partes = linea.split(":")
        if len(partes) >= 3 and partes[1] == "802-11-wireless" and partes[2] == "activated":
            return partes[0]
    return None


def _tabla_señales():
    """Señal (0-100) de TODAS las redes visibles ahora mismo en el scan,
    esten guardadas o no -- separado de listar_redes_visibles() (que
    descarta las ya guardadas) porque esta tabla se usa justo para lo
    contrario: mostrarle intensidad de señal a las redes YA guardadas que
    ademas esten al alcance ahora. Solo lectura, no requiere sudo."""
    r = _nmcli(["-t", "-f", "SSID,SIGNAL", "device", "wifi", "list"])
    if r.returncode != 0:
        log.warning(f"No se pudo escanear señal de redes: {r.stderr.strip()}")
        return {}
    tabla = {}
    for linea in r.stdout.strip().splitlines():
        partes = linea.split(":")
        if len(partes) < 2 or not partes[0]:
            continue
        ssid, señal = partes[0], partes[1]
        señal_num = int(señal) if señal.isdigit() else 0
        # Si el mismo SSID aparece repetido (varios puntos de acceso),
        # se queda con la señal mas fuerte vista.
        if ssid not in tabla or señal_num > tabla[ssid]:
            tabla[ssid] = señal_num
    return tabla


def _barras(señal):
    """Convierte 0-100 a una cantidad de barras 0-4 para el icono. None si
    la red no aparecio en el scan ahora mismo (fuera de alcance o guardada
    pero nunca detectada en esta pasada) -- en ese caso el icono se pinta
    apagado en vez de inventar un valor."""
    if señal is None:
        return None
    if señal >= 75:
        return 4
    if señal >= 50:
        return 3
    if señal >= 25:
        return 2
    if señal > 0:
        return 1
    return 0


def listar_redes_guardadas():
    """Redes wifi guardadas en NetworkManager, con la activa marcada y,
    si esta al alcance ahora mismo, su señal actual (0-100) y barras
    (0-4, o None si no se detecto en el scan). Solo lectura, no requiere
    sudo."""
    activa = _conexion_activa()
    r = _nmcli(["-t", "-f", "NAME,TYPE,AUTOCONNECT-PRIORITY", "connection", "show"])
    if r.returncode != 0:
        log.warning(f"No se pudieron listar redes guardadas: {r.stderr.strip()}")
        return []
    tabla_señal = _tabla_señales()
    redes = []
    for linea in r.stdout.strip().splitlines():
        partes = linea.split(":")
        if len(partes) >= 3 and partes[1] == "802-11-wireless":
            nombre = partes[0]
            señal = tabla_señal.get(nombre)
            redes.append({
                "nombre": nombre,
                "prioridad": partes[2],
                "activa": nombre == activa,
                "señal": señal,
                "barras": _barras(señal),
            })
    redes.sort(key=lambda red: not red["activa"])
    return redes


def listar_redes_visibles():
    """Redes wifi detectables ahora mismo (scan), para sugerir en el
    formulario de agregar. Solo lectura, no requiere sudo. Descarta las
    que ya estan guardadas y deduplica por SSID (puede verse mas de una
    vez si hay varios puntos de acceso repitiendo la misma red)."""
    r = _nmcli(["-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"])
    if r.returncode != 0:
        log.warning(f"No se pudo escanear redes visibles: {r.stderr.strip()}")
        return []
    guardadas = {red["nombre"] for red in listar_redes_guardadas()}
    vistas = {}
    for linea in r.stdout.strip().splitlines():
        partes = linea.split(":")
        if len(partes) < 3 or not partes[0]:
            continue
        ssid, señal, seguridad = partes[0], partes[1], partes[2]
        if ssid in guardadas:
            continue
        señal_num = int(señal) if señal.isdigit() else 0
        if ssid not in vistas or señal_num > vistas[ssid]["señal"]:
            vistas[ssid] = {"ssid": ssid, "señal": señal_num, "abierta": seguridad == ""}
    return sorted(vistas.values(), key=lambda r: -r["señal"])


def rescan_wifi():
    """Dispara un escaneo activo real de NetworkManager -- a diferencia de
    listar_redes_visibles()/_tabla_señales(), que solo LEEN la ultima
    tabla que NetworkManager ya tenia cacheada de su propio ciclo de fondo
    (puede tener minutos de atraso). Esto pide una vuelta de radio nueva
    de verdad. No modifica ninguna conexion guardada (solo lectura desde
    ese punto de vista), pero a diferencia de "device wifi list" (lectura
    de la tabla ya escaneada, permitida sin permisos), pedir un escaneo
    nuevo SI requiere el permiso de NetworkManager "wifi.scan" -- probado
    en vivo, pichiloor no lo tiene sin sudo ("not authorized"), asi que va
    con sudo igual que agregar/modificar/eliminar red. Devuelve False (no
    es grave) si NetworkManager lo rechaza igual por haberse pedido uno
    hace muy poco (lo rate-limitea de su lado)."""
    r = _nmcli(["device", "wifi", "rescan"], usar_sudo=True)
    if r.returncode != 0:
        log.warning(f"No se pudo reescanear wifi (puede ser normal si se pidio hace poco): {r.stderr.strip()}")
        return False
    # El rescan es asincronico del lado de NetworkManager -- esta pausa
    # corta le da tiempo a completar antes de que index() vuelva a listar,
    # sin la cual seguiria devolviendo la tabla vieja.
    time.sleep(3)
    return True


def agregar_red(ssid, password):
    """Agrega una red wifi nueva, SIN conectarse a ella ahora ni tocar la
    conexion activa. Requiere sudo. Devuelve (ok: bool, mensaje: str)."""
    ssid = (ssid or "").strip()
    password = password or ""

    if not ssid or len(ssid) > 32:
        return False, "El nombre de la red (SSID) no es válido."
    if ssid == _conexion_activa():
        return False, "Esa es la red principal actual, no hace falta agregarla de nuevo."
    if password and not (8 <= len(password) <= 63):
        return False, "La contraseña debe tener entre 8 y 63 caracteres (o dejala vacía si es una red abierta)."

    args = [
        "connection", "add", "type", "wifi", "con-name", ssid,
        "ifname", "wlan0", "ssid", ssid,
        "connection.autoconnect", "yes",
        "connection.autoconnect-priority", str(PRIORIDAD_REDES_NUEVAS),
    ]
    if password:
        args += ["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password]

    r = _nmcli(args, usar_sudo=True)
    if r.returncode != 0:
        log.error(f"No se pudo agregar red {ssid!r}: {r.stderr.strip()}")
        return False, "No se pudo guardar la red. Revisá el nombre y la contraseña."

    log.info(f"Red wifi agregada: {ssid!r} (prioridad {PRIORIDAD_REDES_NUEVAS}, sin conectar ahora)")
    return True, f'Red "{ssid}" guardada. Se va a usar automáticamente si la red principal no está disponible.'


def modificar_red(nombre_actual, nuevo_ssid, nueva_password):
    """Cambia el SSID y/o la contraseña de una red de respaldo ya guardada.
    Igual que agregar/eliminar: bloqueado con dureza para la conexion
    activa (no se edita la red en uso, mismo riesgo que eliminarla).
    La contraseña es opcional -- si viene vacia, se deja la que ya tenia
    guardada (nunca se muestra la actual en el formulario, por seguridad,
    asi que "vacio" es la unica forma de decir "no la cambies"). Requiere
    sudo."""
    nombre_actual = (nombre_actual or "").strip()
    nuevo_ssid = (nuevo_ssid or "").strip()
    nueva_password = nueva_password or ""

    if not nombre_actual:
        return False, "Red inválida."
    if nombre_actual == _conexion_activa():
        log.warning(f"Intento de modificar la conexion activa ({nombre_actual!r}) bloqueado")
        return False, "No se puede editar la red a la que estás conectado ahora mismo."
    if not nuevo_ssid or len(nuevo_ssid) > 32:
        return False, "El nombre de la red (SSID) no es válido."
    if nueva_password and not (8 <= len(nueva_password) <= 63):
        return False, "La contraseña debe tener entre 8 y 63 caracteres."

    # Orden importa: la contraseña se cambia PRIMERO, mientras el perfil
    # todavia se llama nombre_actual. Si se renombra antes (connection.id),
    # nmcli ya no reconoce el nombre viejo para el segundo comando -- paso
    # en falso encontrado probando esto a mano antes de desplegarlo.
    if nueva_password:
        r2 = _nmcli(
            ["connection", "modify", nombre_actual, "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", nueva_password],
            usar_sudo=True,
        )
        if r2.returncode != 0:
            log.error(f"No se pudo actualizar contraseña de {nombre_actual!r}: {r2.stderr.strip()}")
            return False, "No se pudo actualizar la contraseña. No se cambió nada."

    # connection.id (el nombre del perfil, lo que se ve en la lista) se
    # actualiza junto con el ssid -- mismo criterio que agregar_red(), que
    # siempre los deja iguales. Va al final porque una vez renombrado,
    # nombre_actual deja de ser un nombre valido para nmcli.
    r = _nmcli(
        ["connection", "modify", nombre_actual, "connection.id", nuevo_ssid, "802-11-wireless.ssid", nuevo_ssid],
        usar_sudo=True,
    )
    if r.returncode != 0:
        log.error(f"No se pudo actualizar SSID de {nombre_actual!r}: {r.stderr.strip()}")
        return False, "No se pudo actualizar el nombre de la red."

    log.info(f"Red wifi modificada: {nombre_actual!r} -> ssid={nuevo_ssid!r}, password_cambiada={bool(nueva_password)}")
    return True, f'Red actualizada: "{nuevo_ssid}".'


def eliminar_red(nombre):
    """Elimina una red guardada. Bloqueado con dureza para la conexion
    activa -- se chequea siempre server-side antes de ejecutar nada, sin
    importar que pida el request. Requiere sudo."""
    nombre = (nombre or "").strip()
    if not nombre:
        return False, "Nombre de red inválido."
    if nombre == _conexion_activa():
        log.warning(f"Intento de eliminar la conexion activa ({nombre!r}) bloqueado")
        return False, "No se puede eliminar la red a la que estás conectado ahora mismo."

    r = _nmcli(["connection", "delete", nombre], usar_sudo=True)
    if r.returncode != 0:
        log.error(f"No se pudo eliminar red {nombre!r}: {r.stderr.strip()}")
        return False, "No se pudo eliminar esa red."

    log.info(f"Red wifi eliminada: {nombre!r}")
    return True, f'Red "{nombre}" eliminada.'


def estado_audio():
    """Estado actual de salida (bocina) y entrada (microfono) de audio,
    solo lectura -- para mostrar en el panel, no controla nada."""
    salida = {"nombre": None, "conectado": False, "estado": None}
    entrada = {"nombre": None, "conectado": False, "estado": None}

    try:
        r = subprocess.run(["bluetoothctl", "devices", "Connected"], capture_output=True, text=True, timeout=10)
        for linea in r.stdout.strip().splitlines():
            partes = linea.split(" ", 2)
            if len(partes) == 3 and partes[0] == "Device":
                salida["nombre"] = partes[2]
                salida["conectado"] = True
                break
    except Exception as e:
        log.warning(f"No se pudo consultar bluetoothctl: {e}")

    try:
        r = subprocess.run(["pactl", "list", "short", "sinks"], capture_output=True, text=True, timeout=10)
        for linea in r.stdout.strip().splitlines():
            if "bluez_output" in linea:
                campos = linea.split("\t")
                salida["estado"] = campos[-1] if campos else None
    except Exception as e:
        log.warning(f"No se pudo consultar pactl sinks: {e}")

    try:
        r = subprocess.run(["arecord", "-l"], capture_output=True, text=True, timeout=10)
        m = re.search(r"card \d+: .*?\[(.+?)\]", r.stdout)
        if m:
            entrada["nombre"] = m.group(1)
    except Exception as e:
        log.warning(f"No se pudo consultar arecord: {e}")

    try:
        r = subprocess.run(["pactl", "list", "short", "sources"], capture_output=True, text=True, timeout=10)
        for linea in r.stdout.strip().splitlines():
            if "alsa_input" in linea:
                campos = linea.split("\t")
                entrada["conectado"] = True
                entrada["estado"] = campos[-1] if campos else None
    except Exception as e:
        log.warning(f"No se pudo consultar pactl sources: {e}")

    return {"salida": salida, "entrada": entrada}
