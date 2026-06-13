"""
rapiro/rapiro_client.py
-----------------------
Protocolo serial del Rapiro para controlar el color de los ojos LED.

Protocolo (57600 baud):
    #PR{r:03d}G{g:03d}B{b:03d}T{t:03d}\r
    Donde T es la duración en décimas de segundo (1000 ms → T010).
"""

import os
import time

import serial

DEFAULT_PORT     = os.environ.get("RAPIRO_SERIAL_PORT", "/dev/ttyAMA0")
DEFAULT_BAUD     = int(os.environ.get("RAPIRO_BAUD_RATE", "57600"))
DEFAULT_DURATION = int(os.environ.get("RAPIRO_LED_DURATION_MS", "1000"))


def build_led_command(red: int, green: int, blue: int, duration_ms: int = DEFAULT_DURATION) -> str:
    """
    Arma el string de comando RGB para los ojos del Rapiro.

    Ejemplo:
        >>> build_led_command(255, 0, 0)
        '#PR255G000B000T010'
    """
    tenths = max(0, int(duration_ms / 100))
    return f"#PR{red:03d}G{green:03d}B{blue:03d}T{tenths:03d}"


def send_led_command(
    red: int,
    green: int,
    blue: int,
    port: str = DEFAULT_PORT,
    baud: int = DEFAULT_BAUD,
    duration_ms: int = DEFAULT_DURATION,
) -> dict:
    """
    Envía el comando de color al Rapiro por serial.

    Devuelve {"ok": bool, "command": str, "message": str}.
    """
    cmd = build_led_command(red, green, blue, duration_ms)
    try:
        with serial.Serial(port, baud, timeout=1.0) as ser:
            time.sleep(0.3)
            ser.write(f"{cmd}\r".encode("ascii"))
            ser.flush()
        return {"ok": True, "command": cmd, "message": "Comando enviado"}
    except serial.SerialException as exc:
        return {"ok": False, "command": cmd, "message": str(exc)}


if __name__ == "__main__":
    # Test rápido: encender ojos en blanco tenue por 2 segundos
    result = send_led_command(100, 100, 100, duration_ms=2000)
    print(result)
