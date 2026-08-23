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
    datetime.time(8, 30),
    datetime.time(18, 0),
    datetime.time(19, 15),
]

# Margen (minutos) alrededor de la hora objetivo, para absorber los retrasos
# del cron de GitHub Actions.
#
# IMPORTANTE: mantenlo por debajo de 15. Tus dos horas de tarde (18:00 y 19:15)
# están a 75 min una de otra y el salto de DST es de 60 min, así que el cron
# "de la otra estación" de las 18:00 cae a sólo 15 min de las 19:15 (y
# viceversa). Con un margen < 15 esos disparos espurios se ignoran y cada
# aviso se envía una sola vez al día. La contrapartida: si Actions se retrasa
# más que este margen, ese aviso se salta ese día (para tiempos de metro en
# tiempo real, un retraso grande ya dejaría los datos obsoletos de todas formas).
TOLERANCIA_MIN = 12

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
            lineas.append(f"⚠️ {nombre}: {e}")
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
