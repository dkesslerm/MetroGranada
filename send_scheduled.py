#!/usr/bin/env python3
"""
Envío programado de tiempos de metro por Telegram, disparado por GitHub Actions.

Diseño TOLERANTE A RETRASOS. El cron de GitHub Actions es best-effort y puede
retrasarse muchísimo (se han visto +100 min en horas punta). Por eso NO se
dispara en el minuto exacto: el workflow corre cada 15 min durante las franjas
de mañana y tarde, y este script decide qué enviar según la hora real de Madrid.

Regla: en cada ejecución se envían los objetivos de HOY cuya hora ya ha pasado
y que aún no se han mandado. Si por un retraso hay varios pendientes a la vez,
se agrupan en un único mensaje (no te llegan copias seguidas). El estado de
"qué se ha enviado hoy" persiste entre ejecuciones vía la caché de Actions.
"""
import datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import urllib3
import requests

from metro import fetch_parada, formato_parada

# metro.py hace requests con verify=False; silenciamos el aviso al importarlo.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MADRID = ZoneInfo("Europe/Madrid")

# Horas LOCALES (Europe/Madrid) a las que quieres recibir el mensaje.
# El DST se maneja solo: la franja del cron es ancha y aquí se compara con la
# hora real de Madrid, así que no tienes que tocar nada al cambiar la hora.
HORARIOS_LOCALES = [
    datetime.time(8, 0),
    datetime.time(8, 15),
    datetime.time(8, 30),
    datetime.time(18, 0),
    datetime.time(18, 30),
    datetime.time(19, 0),
    datetime.time(19, 30),
]

# Paradas que se incluyen en cada aviso automático.
PARADAS_PROGRAMADAS = ["H\u00edpica", "Universidad"]

# Archivo de estado (qu\u00e9 avisos ya se enviaron HOY). Persiste entre
# ejecuciones gracias a la cach\u00e9 de GitHub Actions.
STATE_PATH = Path(os.environ.get("STATE_PATH", "state/sent.json"))


def cargar_estado(hoy):
    """Set de horas ya enviadas hoy. Si el estado es de otro d\u00eda, no existe
    o est\u00e1 corrupto, empieza de cero."""
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if data.get("fecha") == hoy:
            return set(data.get("enviados", []))
    except (FileNotFoundError, ValueError, OSError):
        pass
    return set()


def guardar_estado(hoy, enviados):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps({"fecha": hoy, "enviados": sorted(enviados)}, ensure_ascii=False),
        encoding="utf-8",
    )


def horas_pendientes(ahora, enviados):
    """Objetivos de hoy cuya hora ya pas\u00f3 y que a\u00fan no se han enviado."""
    minutos_ahora = ahora.hour * 60 + ahora.minute
    pendientes = []
    for t in HORARIOS_LOCALES:
        clave = t.strftime("%H:%M")
        if minutos_ahora >= t.hour * 60 + t.minute and clave not in enviados:
            pendientes.append(clave)
    return pendientes


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
    # FORCE_SEND lo pone el workflow al lanzarlo a mano (workflow_dispatch):
    # env\u00eda una vez para probar y NO toca el estado del d\u00eda.
    forzar = bool(os.environ.get("FORCE_SEND"))
    ahora = datetime.datetime.now(MADRID)
    hoy = ahora.strftime("%Y-%m-%d")

    enviados = cargar_estado(hoy)
    pendientes = horas_pendientes(ahora, enviados)

    if not forzar and not pendientes:
        ya = sorted(enviados) or "ninguno"
        print(f"Nada pendiente a las {ahora:%H:%M} (Madrid). Ya enviados hoy: {ya}.")
        return

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["CHAT_ID"]

    # Un solo mensaje por ejecuci\u00f3n: si hay varios objetivos atrasados,
    # se saldan todos con un \u00fanico aviso.
    enviar_telegram(token, chat_id, construir_mensaje())

    if forzar:
        print("Env\u00edo forzado (prueba manual). No se modifica el estado.")
        return

    enviados.update(pendientes)
    guardar_estado(hoy, enviados)
    print(f"Enviado. Objetivos cubiertos: {pendientes}. Total hoy: {sorted(enviados)}.")


if __name__ == "__main__":
    main()