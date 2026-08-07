# 🕶️ Gafas ultrasónicas

Asistente de voz para personas no videntes, corriendo en una Raspberry Pi que se lleva encima. Escucha una palabra de activación, toma una foto, y describe la escena, lee un texto en voz alta, o avisa de obstáculos cercanos — según lo que se le pida — todo en español.

## Cómo funciona (arquitectura)

```
wake.py  →  boton.py  →  camara.py  →  vertex_context_vision.py  →  tts_cloud.py
(escucha)   (orquesta)   (foto)        (describe/lee con Gemini)    (habla)
```

1. **`wake.py`** escucha el micrófono todo el tiempo y detecta la palabra de activación **localmente** con [Vosk](https://alphacephei.com/vosk/) (modelo `vosk-model-small-es-0.42`) — el audio nunca sale de la Raspberry Pi solo por estar escuchando.
2. Al detectar la activación, dispara **`boton.py`**, que:
   - toma una foto con **`camara.py`** (cámara IMX519, autoenfoque real),
   - la manda a **`vertex_context_vision.py`**, que la describe o lee con **Gemini** (Google Vertex AI),
   - y reproduce la respuesta con **`tts_cloud.py`** (Google Cloud Text-to-Speech).
3. Todo el ciclo se registra en `logs/` con un ID único, y las fotos/audios de cada interacción quedan guardados junto al log del día.

### Los 3 modos

Antes de pedir la foto, se puede decir una palabra reservada para elegir **qué tipo de respuesta** se necesita. El modo elegido aplica solo a la próxima foto; si no se dice ninguno, usa **entorno** por defecto.

| Modo | Se activa diciendo | Qué hace |
|---|---|---|
| **Entorno** | "gafas, entorno" | Describe el lugar en general: qué hay, quién hay, cómo está todo ubicado. |
| **Lectura** | "gafas, lectura" / "gafas, leer" / "gafas, texto" / "gafas, lee" | Lee en voz alta cualquier texto que encuentre (letreros, libros, etiquetas). |
| **Obstáculos** | "gafas, obstáculos" / "gafas, obstáculo" / "gafas, peligro" | Avisa qué obstáculos hay cerca y en qué dirección, para caminar seguro — usa una **distancia estimada** a partir del punto donde enfocó la cámara (ver nota abajo). |

Los prompts de cada modo están en `prompts/entorno.txt`, `prompts/lectura.txt` y `prompts/obstaculos.txt` (editables sin tocar código; si un archivo falta o está roto, `vertex_context_vision.py` usa un respaldo interno).

> **Nota sobre "ultrasónicas":** pese al nombre, la distancia no se mide con un sensor ultrasónico físico — se **estima** a partir del `LensPosition` que reporta el autoenfoque de la cámara (dioptrías → metros). Es una referencia aproximada de un solo punto (el que la cámara decidió enfocar), no un sensor calibrado.

Además, cualquiera de las **frases de saludo** configurables (ver panel web) hace que las gafas respondan solo con un saludo, sin tomar foto — sirve para confirmar que están escuchando.

## Hardware

- **Raspberry Pi Zero 2 W** (512MB RAM) con **PiSugar** (HAT de batería/UPS) — el usuario apaga/reinicia manualmente para administrar batería.
- Cámara **IMX519** (autoenfoque físico real, ~7-9s por captura — es el piso físico del motor de enfoque, no una mala configuración).
- Micrófono **USB** (`C-Media USB PnP Sound Device`).
- Parlante **Bluetooth Anker SoundCore** (salida de audio).
- Sin pantalla ni teclado conectados — todo el manejo es remoto por SSH o por el panel web.

## Servicios (systemd de usuario)

Todo corre como servicios de **usuario** (`systemctl --user`, no `sudo systemctl`), habilitados con `linger` para que arranquen solos sin necesitar sesión iniciada.

| Servicio | Qué hace |
|---|---|
| `wake.service` | El proceso principal: escucha y dispara el ciclo completo. `Restart=always`. |
| `config-web.service` | Panel web de configuración (Flask, puerto **8080**, con login). Ver abajo. |
| `set-audio-bt.service` | Conecta el parlante Bluetooth al arrancar, con reintentos (el Anker a veces tarda en aparecer). |
| `limpiar-logs.timer` | Corre `limpiar_logs_viejos.py` ~2 min después de cada arranque — borra carpetas de log más viejas que `RETENCION_DIAS`. |

Comandos básicos (aplican a los 4, cambiando el nombre):
```bash
systemctl --user status wake.service
systemctl --user restart wake.service
journalctl --user -u wake.service -f
```

## Panel web de configuración

Accesible en `http://<ip-de-la-pi>:8080` (solo red local, sin HTTPS — no pensado para exponerse a internet), con login usuario/contraseña. Permite, sin entrar por SSH:

- Nombre y saludo de bienvenida (con audio cacheado, no se regenera si no cambió nada).
- Voz (femenino/masculino) y velocidad de habla.
- Nivel de detalle de las descripciones (breve/detallado).
- Frases de saludo (hasta 5).
- Redes WiFi guardadas: ver señal real, agregar (con combo de redes detectadas cerca o SSID manual), editar o eliminar redes de respaldo — la red **principal** (la que está conectada ahora) siempre queda protegida y no se puede tocar desde acá, para no perder el acceso remoto a la Pi.
- Estado de los dispositivos de audio (bocina/micrófono).

Guardar aplica el cambio al instante (reinicia `wake.service` solo).

## Configuración y credenciales

- **`.env`** (no versionado, ver `.env.example`): credenciales de Google Cloud y variables ajustables — `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `VERTEX_GEMINI_MODEL`, `RETENCION_DIAS`, `MAX_PALABRAS_LECTURA`.
- **`config.json`** (no versionado, ver `config.example.json`): lo que edita el panel web (nombre, saludo, voz, frases, nivel de detalle). Se valida siempre con respaldo a valores por defecto si el archivo falta o está mal formado.
- **`web_auth.json`** (no versionado): usuario y hash de la contraseña del panel web.
- Credenciales de Google Cloud (service account JSON) viven fuera del repo, en `~/secrets/`.

## Logs

```
logs/YYYY/MM/DD/
  20260804-201814-6d94.jpg   ← foto de un ciclo
  20260804-201814-6d94.mp3   ← audio de la respuesta (mismo ciclo)
  2026-08-04.log             ← log completo del día
```

Cada línea de log lleva un `cycle_id` (`YYYYMMDD-HHMMSS-XXXX`) que conecta la foto, el audio y las 4-5 líneas de log de ese mismo ciclo, en todos los módulos (`wake`, `boton`, `camara`, `vertex`, `tts`). Se limpian solas pasados `RETENCION_DIAS` (180 por defecto).

## Instalar / dependencias

Python 3.11, principales paquetes: `flask`, `vosk`, `sounddevice`, `picamera2`, `google-genai`, `google-cloud-texttospeech`. `rpicam-still` (captura de foto) y `mpg123`/`aplay` (reproducción) son binarios del sistema, no de pip.

## Entorno gráfico

La Pi corre sin interfaz gráfica (modo consola) para ahorrar RAM — cambio **permanente**, no solo de la sesión actual:
```bash
sudo systemctl set-default multi-user.target   # sin entorno gráfico (estado actual)
sudo systemctl set-default graphical.target    # revertir, si hiciera falta
```
