#!/usr/bin/python3
"""
Panel web liviano (Flask) para editar config.json sin entrar por SSH.
Corre solo en la red local -- no pensado para exponerse a internet.
Login con usuario/contraseña (hash guardado en web_auth.json, nunca en
texto plano). Al guardar, valida con la misma logica de config.py y
reinicia wake.service para que el cambio se aplique al toque.
"""
import os
import json
import time
import subprocess
from functools import wraps
from flask import Flask, request, redirect, url_for, session, render_template

from logger import get_logger
from config import CONFIG_PATH, VOCES, NIVELES_DETALLE, _validar, MODOS_RESERVADOS, DESCRIPCIONES_MODOS
import red

log = get_logger("config_web")

# Presets para el slider de velocidad en la web -- en vez de un numero
# libre, el usuario elige entre estas paradas fijas.
VELOCIDAD_PRESETS = [
    (0.75, "Lento"),
    (1.0, "Normal"),
    (1.25, "Rápido"),
    (1.5, "Muy rápido"),
]


def etiqueta_velocidad(valor):
    """Nombre del preset mas cercano a un valor de velocidad dado."""
    return min(VELOCIDAD_PRESETS, key=lambda p: abs(p[0] - valor))[1]


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_PATH = os.path.join(BASE_DIR, "web_auth.json")

with open(AUTH_PATH, "r") as f:
    AUTH = json.load(f)

app = Flask(__name__)
app.secret_key = AUTH["secret_key"]


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        usuario = request.form.get("usuario", "")
        clave = request.form.get("clave", "")
        # werkzeug maneja el hash/verificacion; comparacion de usuario
        # simple porque no es informacion secreta (la clave si lo es).
        from werkzeug.security import check_password_hash
        if usuario == AUTH["usuario"] and check_password_hash(AUTH["password_hash"], clave):
            session["logged_in"] = True
            log.info(f"Login OK: {usuario}")
            return redirect(url_for("index"))
        log.warning(f"Login fallido: usuario={usuario!r}")
        time.sleep(1)  # freno simple ante intentos repetidos
        error = "Usuario o contraseña incorrectos"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/red/agregar", methods=["POST"])
@login_required
def red_agregar():
    """Guarda una red wifi nueva (sin conectarse ni tocar la red activa,
    ver red.agregar_red). No renderiza directo -- redirige a index() para
    evitar que un refresh de pagina reenvie el formulario."""
    ok, msg = red.agregar_red(request.form.get("ssid", ""), request.form.get("password", ""))
    session["flash"] = msg
    if not ok:
        log.warning(f"Fallo al agregar red desde la web: {msg}")
    return redirect(url_for("index"))


@app.route("/red/modificar", methods=["POST"])
@login_required
def red_modificar():
    """Cambia SSID y/o contraseña de una red de respaldo. red.modificar_red()
    bloquea del lado del servidor si es la conexion activa."""
    ok, msg = red.modificar_red(
        request.form.get("nombre_actual", ""),
        request.form.get("ssid", ""),
        request.form.get("password", ""),
    )
    session["flash"] = msg
    if not ok:
        log.warning(f"Fallo al modificar red desde la web: {msg}")
    return redirect(url_for("index"))


@app.route("/red/rescan", methods=["POST"])
@login_required
def red_rescan():
    """Pide un escaneo wifi activo de verdad (no solo lee la ultima tabla
    cacheada de NetworkManager) antes de volver a index() -- para el boton
    de "buscar redes cercanas de nuevo" junto a "Agregar una red nueva"."""
    ok = red.rescan_wifi()
    session["flash"] = "Redes cercanas actualizadas." if ok else "No se pudo reescanear ahora mismo, se muestran las últimas detectadas."
    return redirect(url_for("index"))


@app.route("/red/eliminar", methods=["POST"])
@login_required
def red_eliminar():
    """Elimina una red guardada. red.eliminar_red() bloquea del lado del
    servidor si es la conexion activa -- no depende de que el HTML no
    muestre el boton, por si alguien arma el request a mano."""
    ok, msg = red.eliminar_red(request.form.get("nombre", ""))
    session["flash"] = msg
    if not ok:
        log.warning(f"Fallo al eliminar red desde la web: {msg}")
    return redirect(url_for("index"))


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    mensaje = session.pop("flash", None)
    if request.method == "POST":
        nuevo = {
            "nombre_usuario": request.form.get("nombre_usuario", ""),
            "saludo": request.form.get("saludo", ""),
            "genero_voz": request.form.get("genero_voz", ""),
            "nivel_detalle": request.form.get("nivel_detalle", ""),
            "frases_activacion": [
                f.strip() for f in request.form.getlist("frases_activacion") if f.strip()
            ],
        }
        try:
            nuevo["velocidad_habla"] = float(request.form.get("velocidad_habla", 1.0))
        except ValueError:
            nuevo["velocidad_habla"] = None

        validado = _validar(nuevo)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(validado, f, indent=2, ensure_ascii=False)
        log.info(f"Config actualizada desde la web: {validado}")

        try:
            subprocess.run(
                ["systemctl", "--user", "restart", "wake.service"],
                check=True, timeout=15,
            )
            mensaje = "Guardado y aplicado."
        except Exception as e:
            log.error(f"No se pudo reiniciar wake.service desde la web: {e}")
            mensaje = "Guardado, pero no se pudo reiniciar el servicio solo. Reinicialo a mano."

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Separada aca (no en el template) para que el HTML no tenga que andar
    # filtrando cual es la activa -- red.py ya la marca, esto solo la separa
    # del resto para que la web la muestre distinto (protegida vs. respaldo).
    # Se pasa el dict completo (no solo el nombre) para tener tambien
    # "barras"/"señal" disponibles en el template.
    redes = red.listar_redes_guardadas()
    red_principal = next((r for r in redes if r["activa"]), None)
    otras_redes = [r for r in redes if not r["activa"]]

    return render_template(
        "config.html",
        cfg=cfg,
        voces=list(VOCES.keys()),
        niveles=list(NIVELES_DETALLE.keys()),
        velocidad_presets=VELOCIDAD_PRESETS,
        velocidad_label=etiqueta_velocidad(cfg["velocidad_habla"]),
        mensaje=mensaje,
        modos_reservados=MODOS_RESERVADOS,
        modos_descripciones=DESCRIPCIONES_MODOS,
        # Todas las frases reservadas en una sola lista, sin agrupar por
        # modo -- el JS del panel solo necesita saber "esta reservada o
        # no", no a que modo pertenece cada una.
        frases_reservadas_flat=[f for frases in MODOS_RESERVADOS.values() for f in frases],
        red_principal=red_principal,
        otras_redes=otras_redes,
        redes_visibles=red.listar_redes_visibles(),
        audio=red.estado_audio(),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
