"""
rapiro/actuator.py  —  corre en la Raspberry Pi 2B.

Pollea GET /comando en la API cloud y manda el color al Rapiro por serial.

Uso:
    python actuator.py               # producción (lee .env)
    DRY_RUN=1 python actuator.py     # sin Rapiro físico, solo imprime la secuencia
    DEBUG=1   python actuator.py     # imprime cada poll (diagnóstico fino)

Variables (en .env o como env vars):
    API_URL            URL de la API en EC2  (obligatorio)
    RAPIRO_SERIAL_PORT puerto serial          (default: /dev/ttyAMA0)
    RAPIRO_BAUD_RATE   baud rate              (default: 57600)
    POLL_INTERVAL_S    segundos entre polls   (default: 1.0)
    DRY_RUN            1/true/yes → no manda serial (vacío, 0, false, no → off)
    DEBUG              1/true/yes → log por cada poll
"""

import os
import time
import signal

import requests
from dotenv import load_dotenv

from rapiro_client import run_behavior, build_behavior

load_dotenv()


def _flag(nombre: str) -> bool:
    """Lee un flag booleano de entorno. '', '0', 'false', 'no' → False; resto → True."""
    return os.environ.get(nombre, "").strip().lower() not in ("", "0", "false", "no")


API_URL       = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL_S", "1.0"))
DRY_RUN       = _flag("DRY_RUN")
DEBUG         = _flag("DEBUG")
ENDPOINT      = f"{API_URL}/comando"
HEALTH        = f"{API_URL}/health"

_ultimo_ts: float = 0.0
_corriendo: bool = True
_conectado: "bool | None" = None     # None = nunca probó; rastrea cambios de estado de red
_espera_logueada: bool = False       # para loguear "esperando comando" una sola vez


def _stop(*_):
    global _corriendo
    _corriendo = False


signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGTERM, _stop)


def _set_conectado(ok: bool) -> None:
    """Loguea SOLO cuando cambia el estado de conexión (no spamea en cada poll)."""
    global _conectado
    if ok and _conectado is not True:
        print(f"[rapiro] conectado a {API_URL}")
    elif not ok and _conectado is not False:
        print(f"[rapiro] SIN conexión a {API_URL} — reintentando cada {POLL_INTERVAL}s")
    _conectado = ok


def poll_y_actuar() -> None:
    global _ultimo_ts, _espera_logueada

    try:
        resp = requests.get(ENDPOINT, timeout=5)
    except requests.exceptions.RequestException as exc:
        _set_conectado(False)
        if DEBUG:
            print(f"[rapiro][debug] error de red: {exc}")
        return

    _set_conectado(True)

    if resp.status_code == 204:
        # Buzón vacío: la API está viva pero todavía nadie clasificó nada.
        if not _espera_logueada:
            print("[rapiro] conectado, esperando primera clasificación...")
            _espera_logueada = True
        if DEBUG:
            print("[rapiro][debug] 204 (buzon vacio)")
        return

    if resp.status_code != 200:
        if DEBUG:
            print(f"[rapiro][debug] HTTP {resp.status_code}")
        return

    data  = resp.json()
    ts    = float(data.get("ts", 0))
    color = data.get("color", [40, 40, 40])
    clase = data.get("clase", "?")

    if ts <= _ultimo_ts:
        if DEBUG:
            print(f"[rapiro][debug] comando repetido (ts={ts}), sin cambios")
        return

    _ultimo_ts = ts
    _espera_logueada = False
    rgb = (int(color[0]), int(color[1]), int(color[2]))

    if DRY_RUN:
        cmds = " ".join(c for c, _ in build_behavior(clase, rgb))
        print(f"[rapiro] {clase} → {cmds}")
        return

    print(f"[rapiro] {clase} → RGB{rgb}")
    resultado = run_behavior(clase, rgb)
    if not resultado["ok"]:
        print(f"[rapiro] ERROR serial: {resultado['message']}")


def _health_check() -> None:
    """Chequeo inicial: avisa si la API está viva y si el modelo cargó."""
    try:
        resp = requests.get(HEALTH, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            estado = "modelo cargado" if data.get("model_loaded") else "modelo NO cargado (aun arrancando?)"
            print(f"[rapiro] API en linea ({estado})")
        else:
            print(f"[rapiro] API respondio HTTP {resp.status_code} en /health")
    except requests.exceptions.RequestException as exc:
        print(f"[rapiro] no se pudo contactar la API en el arranque: {exc}")
        print(f"[rapiro] verifica API_URL={API_URL} y que la EC2 este levantada")


def main():
    modo = "DRY RUN" if DRY_RUN else "PRODUCCION"
    print(f"[rapiro] iniciando ({modo}) — API_URL={API_URL}")
    _health_check()

    while _corriendo:
        poll_y_actuar()
        time.sleep(POLL_INTERVAL)

    print("[rapiro] detenido.")


if __name__ == "__main__":
    main()
