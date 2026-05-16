#!/usr/bin/env python3
import sys
import time
import requests
from bs4 import BeautifulSoup

ENDPOINT = "https://metropolitanogranada.es/MGhorariosreal.asp"


def fetch_todas():
    """Devuelve dict {nombre_parada: {albolote_1, albolote_2, armilla_1, armilla_2}}."""
    resp = requests.post(
        ENDPOINT,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Content-Length": "0",
        },
        data="",
        timeout=10,
        verify=False,
    )
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    resultado = {}
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 5:
            continue
        nombre = cells[0].get_text(strip=True)
        tiempos = [c.get_text(strip=True) for c in cells[1:]]
        resultado[nombre] = {
            "albolote_1": tiempos[0],
            "albolote_2": tiempos[1],
            "armilla_1": tiempos[2],
            "armilla_2": tiempos[3],
        }
    return resultado


def fetch_parada(nombre):
    todas = fetch_todas()
    if nombre not in todas:
        raise ValueError(f"Parada '{nombre}' no encontrada")
    return todas[nombre]


def formato_parada(nombre, t):
    return (
        f"🚇 {nombre}\n"
        f"➡️  Albolote:  {t['albolote_1']}  /  {t['albolote_2']}\n"
        f"⬅️  Armilla:   {t['armilla_1']}  /  {t['armilla_2']}"
    )


if __name__ == "__main__":
    import os

    requests.packages.urllib3.disable_warnings()

    parada = sys.argv[1] if len(sys.argv) > 1 else "Hípica"
    print(f"Metro Granada — {parada} (Ctrl+C para salir)\n")
    try:
        while True:
            try:
                t = fetch_parada(parada)
                os.system("clear")
                print(formato_parada(parada, t))
            except Exception as e:
                print(f"Error: {e}")
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nHasta luego.")
        sys.exit(0)
