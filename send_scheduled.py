#!/usr/bin/env python3
"""
Envío programado de tiempos de metro por Telegram, disparado por GitHub Actions.

Por qué existe este archivo (y no un JobQueue en un servidor):
    El cron de GitHub Actions sólo entiende UTC y NO sabe de cambios de hora
    (DST). Por eso el workflow dispara en TODOS los offsets UTC posibles
    (verano UTC+2 e invierno UTC+1) para cada hora local deseada, y este script
    decide si de verdad toca enviar comprobando la hora local de Madrid.
    Las ejecuciones "de más" simplemente no hacen nada y salen.
"""
import datetime
import os
from zoneinfo import ZoneInfo

import urllib3
import requests

from metro import fetch_parada, formato_parada

# metro.py hace requests con verify=False; silenciamos el aviso al importarlo.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MADRID = ZoneInfo("Europe/Madrid")

# Horas LOCALES (Europe/Madrid) a las que quieres recibir el mensaje.
# El DST se maneja solo: no tienes que tocar nada al cambiar la hora.
HORARIOS_LOCALES = [
    datetime.time(8, 0),
    datetime.time(8, 15),
    datetime.time(8, 30),
    datetime.time(18, 0),
    datetime.time(18, 30),
    datetime.time(19, 0),
    datetime.time(19, 30),
]

# Margen (minutos) alrededor de la hora objetivo, para absorber los retrasos
# del cron de GitHub Actions.
#
# IMPORTANTE: mantenlo por debajo de 30. Con estas horas, el disparo "de la otra
# estación" más cercano cae a 30 min de un objetivo, así que con un margen < 30
# se descarta solo y cada aviso se envía una vez al día. Contrapartidas:
#   - Si Actions se retrasa MÁS que este margen, ese aviso se salta ese día.
#   - Baja hacia 10 si quieres evitar del todo duplicados por retrasos grandes;
#     sube hacia 25 si prefieres no perder ninguno (pero siempre < 30).
TOLERANCIA_MIN = 20

# Paradas que se incluyen en cada aviso automático.
PARADAS_PROGRAMADAS = ["Hípica", "Universidad"]


def toca_enviar(ahora=None):
    """¿La hora local actual está dentro del margen de alguna hora objetivo?"""
    ahora = ahora or datetime.datetime.now(MADRID)
    minutos_ahora = ahora.hour * 60 + ahora.minute
    for t in HORARIOS_LOCALES:
        objetivo = t.hour * 60 + t.minute
        if abs(minutos_ahora - objetivo) <= TOLERANCIA_MIN:
            return True
    return False


def construir_mensaje():
    lineas = []
    for nombre in PARADAS_PROGRAMADAS:
        try:
            t = fetch_parada(nombre)
            lineas.append(formato_parada(nombre, t))
        except Exception as e:
            lineas.append(f"\u26a0\ufe0f {nombre}: {e}")
    return "\n\n".join(lineas)


def enviar_telegram(token, chat_id, texto):
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": texto},
        timeout=15,
    )
    resp.raise_for_status()


def main():
    # FORCE_SEND lo pone el workflow cuando lo lanzas a mano (workflow_dispatch),
    # para poder probar el envío a cualquier hora saltándote la comprobación.
    forzar = bool(os.environ.get("FORCE_SEND"))
    if not forzar and not toca_enviar():
        ahora = datetime.datetime.now(MADRID).strftime("%H:%M")
        print(f"No toca enviar a las {ahora} (Madrid). Saliendo sin enviar.")
        return

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["CHAT_ID"]

    enviar_telegram(token, chat_id, construir_mensaje())
    print("Mensaje enviado.")


if __name__ == "__main__":
    main()