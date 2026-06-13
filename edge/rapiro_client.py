"""
edge/rapiro_client.py
---------------------
Copiado y simplificado de grupo-stefi/PruebaRapiro/src/rapiro_client.py.

Solo se mantiene lo necesario para el actuador de la Pi:
  - build_led_command(r, g, b, duration_ms) → str   arma el comando de ojos
  - send_led_command(r, g, b, port, baud)            manda el comando por serial

El resto del cliente original (servos, motions, clase completa) se omite
para mantener este módulo simple y sin dependencias extra.

Protocolo Rapiro (serial, 57600 baud):
    #PR{r:03d}G{g:03d}B{b:03d}T{t:03d}\\r
    Donde T es la duración en décimas de segundo (500 ms → T005).
"""

import os
import time

import serial

# Configuración por defecto (puede sobreescribirse con variables de entorno)
DEFAULT_PORT     = os.environ.get("RAPIRO_SERIAL_PORT", "/dev/ttyAMA0")
DEFAULT_BAUD     = int(os.environ.get("RAPIRO_BAUD_RATE", "57600"))
DEFAULT_DURATION = int(os.environ.get("RAPIRO_LED_DURATION_MS", "1000"))  # 1 segundo


def build_led_command(red: int, green: int, blue: int, duration_ms: int = DEFAULT_DURATION) -> str:
    """
    Arma el comando de color de ojos RGB del Rapiro.

    Parámetros
    ----------
    red, green, blue : int
        Valores RGB en [0, 255].
    duration_ms : int
        Duración en milisegundos. Se convierte a décimas de segundo (T).

    Devuelve
    --------
    str — por ejemplo: "#PR255G000B000T010" para rojo durante 1 segundo.

    Ejemplo:
        >>> build_led_command(255, 255, 0)
        '#PR255G255B000T010'
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
    Envía el comando de color a los ojos del Rapiro por serial.

    Devuelve un dict con {"ok": bool, "command": str, "message": str}.
    En caso de error serial devuelve ok=False con el mensaje de error.
    """
    cmd = build_led_command(red, green, blue, duration_ms)
    try:
        with serial.Serial(port, baud, timeout=1.0) as ser:
            time.sleep(0.3)          # esperar a que el puerto esté listo
            ser.write(f"{cmd}\r".encode("ascii"))
            ser.flush()
        return {"ok": True, "command": cmd, "message": "Comando enviado"}
    except serial.SerialException as exc:
        return {"ok": False, "command": cmd, "message": str(exc)}


if __name__ == "__main__":
    # Test rápido: encender ojos en blanco por 2 segundos
    result = send_led_command(100, 100, 100, duration_ms=2000)
    print(result)
