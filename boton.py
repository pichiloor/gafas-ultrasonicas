#!/usr/bin/python3

from camara import tomar_foto
#from vision_mix_cloud import analizar_imagen_cloud as extraer_texto
import os
from diccionario import traducir
import subprocess

SHUTTER_SOUND = "/home/pichiloor/Documents/camera-shutter.mp3"

def play_sound(path):
    subprocess.Popen(["mpg123", "-q", path])

#hablar("¡Tomando foto!")
def ejecutar():
    # Imports diferidos: vertex_context_vision y tts_cloud cargan SDKs
    # pesados de Google (grpc/protobuf). Se importan aqui (no al tope del
    # modulo) para que ese peso solo se cargue en RAM cuando de verdad se
    # necesita (primera activacion), no todo el tiempo que el servicio
    # esta solo escuchando el wake word. Python cachea el import, asi que
    # en llamadas siguientes no hay costo extra (el cliente persistente
    # de cada modulo se sigue creando una sola vez).
    from vertex_context_vision import describir_o_leer
    from tts_cloud import hablar

    ruta = tomar_foto()

    if not ruta or not os.path.exists(ruta):
        hablar("No se pudo tomar la foto.")
        return

    play_sound(SHUTTER_SOUND)
    # texto, objetos, etiquetas = extraer_texto(ruta)

    # mensaje = ""

    # if etiquetas:
    #     etiquetas_lista = ", ".join(traducir(e.lower()) for e in etiquetas)
    #     mensaje += f"Veo una escena relacionada con: {etiquetas_lista}. "
    # if objetos:
    #     obj_lista = ", ".join(traducir(obj.lower()) for obj in objetos)
    #     mensaje += f"He detectado objetos como: {obj_lista}. "

    # if texto:
    #     mensaje += f"El texto dice: {texto}"
    # else:
    #     mensaje += "No se detectó texto legible." 

    mensaje = describir_o_leer(ruta)
    print(mensaje)
    hablar(mensaje)


if __name__ == "__main__":
    ejecutar()
