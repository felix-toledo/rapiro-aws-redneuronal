"""
rapiro/actuator.py  —  corre en la Raspberry Pi 2B.

Pollea GET /comando en la API cloud y manda el color al Rapiro por serial.

Uso:
    python actuator.py               # producción (lee .env)
    DRY_RUN=1 python actuator.py     # sin Rapiro físico, solo imprime

Variables (en .env o como env vars):
    API_URL            URL de la API en EC2  (obligatorio)
    RAPIRO_SERIAL_PORT puerto serial          (default: /dev/ttyAMA0)
    RAPIRO_BAUD_RATE   baud rate              (default: 57600)
    POLL_INTERVAL_S    segundos entre polls   (default: 1.0)
    DRY_RUN            cualquier valor → no manda serial
"""

import os
import time
import signal

import requests
from dotenv import load_dotenv

from rapiro_client import send_led_command

load_dotenv()

API_URL       = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL_S", "1.0"))
DRY_RUN       = bool(os.environ.get("DRY_RUN", ""))
ENDPOINT      = f"{API_URL}/comando"

_ultimo_ts: float = 0.0
_corriendo: bool = True


def _stop(*_):
    global _corriendo
    _corriendo = False


signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGTERM, _stop)


def poll_y_actuar() -> None:
    global _ultimo_ts

    try:
        resp = requests.get(ENDPOINT, timeout=5)
    except requests.exceptions.RequestException:
        return  # sin conexión, siguiente poll

    if resp.status_code == 204 or resp.status_code != 200:
        return

    data  = resp.json()
    ts    = float(data.get("ts", 0))
    color = data.get("color", [40, 40, 40])
    clase = data.get("clase", "?")

    if ts <= _ultimo_ts:
        return

    _ultimo_ts = ts
    r, g, b = int(color[0]), int(color[1]), int(color[2])

    print(f"[rapiro] {clase} → R={r} G={g} B={b}")

    if DRY_RUN:
        return

    resultado = send_led_command(r, g, b)
    if not resultado["ok"]:
        print(f"[rapiro] ERROR serial: {resultado['message']}")


def main():
    modo = "DRY RUN" if DRY_RUN else "PRODUCCION"
    print(f"[rapiro] iniciando ({modo}) — {API_URL}")

    while _corriendo:
        poll_y_actuar()
        time.sleep(POLL_INTERVAL)

    print("[rapiro] detenido.")


if __name__ == "__main__":
    main()
