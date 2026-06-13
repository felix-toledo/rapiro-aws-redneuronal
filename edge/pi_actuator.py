"""
edge/pi_actuator.py
-------------------
Corre en la Raspberry Pi 2B.

Loop de polling: cada ~1 segundo hace GET /comando a la API en la nube (o local).
Si la respuesta tiene un color nuevo, lo manda al Rapiro por serial.

Por qué polling y no push:
    La Pi está detrás de un NAT sin IP pública. La EC2 no puede iniciar
    conexión hacia ella. La Pi pregunta periódicamente → funciona detrás
    de cualquier router sin abrir puertos.

Uso:
    # Contra API local (debug):
    API_URL=http://<ip-notebook>:8000 python edge/pi_actuator.py

    # Contra EC2 (producción):
    API_URL=http://<ip-ec2>:8000 python edge/pi_actuator.py

Variables de entorno:
    API_URL            URL base de la API (obligatorio en producción)
    RAPIRO_SERIAL_PORT Puerto serial del Rapiro (default: /dev/ttyAMA0)
    RAPIRO_BAUD_RATE   Baud rate (default: 57600)
    POLL_INTERVAL_S    Segundos entre polls (default: 1.0)
    DRY_RUN            Si está definida, no manda serial (solo imprime el cmd)
"""

import os
import time
import signal
import sys

import requests

from edge.rapiro_client import build_led_command, send_led_command

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
API_URL         = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")
POLL_INTERVAL   = float(os.environ.get("POLL_INTERVAL_S", "1.0"))
DRY_RUN         = bool(os.environ.get("DRY_RUN", ""))
ENDPOINT        = f"{API_URL}/comando"

# Puerto y baud los lee rapiro_client desde sus propias env vars.


# ---------------------------------------------------------------------------
# Estado del actuador
# ---------------------------------------------------------------------------
_ultimo_ts: float = 0.0          # timestamp del último comando ejecutado
_corriendo: bool = True


def _signal_handler(sig, frame):
    """Maneja Ctrl+C de forma limpia."""
    global _corriendo
    print("\n[pi_actuator] Deteniendo...")
    _corriendo = False


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


# ---------------------------------------------------------------------------
# Funciones
# ---------------------------------------------------------------------------

def poll_y_actuar() -> None:
    """
    Hace GET /comando y, si hay un color nuevo (ts mayor al último ejecutado),
    lo manda al Rapiro por serial.
    """
    global _ultimo_ts

    try:
        resp = requests.get(ENDPOINT, timeout=5)
    except requests.exceptions.RequestException as exc:
        print(f"[WARN] Sin conexión con la API: {exc}")
        return

    if resp.status_code == 204:
        # Sin clasificaciones aún — no hay nada que hacer
        return

    if resp.status_code != 200:
        print(f"[WARN] GET /comando respondió {resp.status_code}")
        return

    data = resp.json()
    ts   = float(data.get("ts", 0))
    color = data.get("color", [40, 40, 40])
    clase = data.get("clase", "?")

    # Solo actuar si el timestamp es más nuevo que el último que procesamos
    if ts <= _ultimo_ts:
        return   # mismo comando → no repetir

    _ultimo_ts = ts
    r, g, b = int(color[0]), int(color[1]), int(color[2])
    cmd = build_led_command(r, g, b)

    print(f"[pi_actuator] Nueva clase: {clase}  → ojos R={r} G={g} B={b}  cmd={cmd}")

    if DRY_RUN:
        print("[pi_actuator] DRY_RUN: comando NO enviado por serial.")
        return

    resultado = send_led_command(r, g, b)
    if resultado["ok"]:
        print(f"[pi_actuator] Serial OK: {resultado['command']}")
    else:
        print(f"[pi_actuator] Error serial: {resultado['message']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Rapiro Pi Actuator ===")
    print(f"  API URL  : {API_URL}")
    print(f"  Intervalo: {POLL_INTERVAL}s")
    if DRY_RUN:
        print("  [DRY RUN] No se enviará serial real.")
    print("  Ctrl+C para detener.\n")

    while _corriendo:
        poll_y_actuar()
        time.sleep(POLL_INTERVAL)

    print("[pi_actuator] Terminado.")


if __name__ == "__main__":
    main()
