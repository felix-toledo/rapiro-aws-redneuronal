"""
rapiro/rapiro_client.py
-----------------------
Protocolo serial del Rapiro. Formatos y tiempos verificados contra el
firmware oficial (RAPIRO_ver0_0.ino) y el script probado en hardware real
de grupo-stefi (PruebaRapiro/src/test.py).

Comandos que entiende la placa (todos terminan en \r, ASCII, 57600 baud):
    #M{n}                       motion pre-grabada 0-9 (UN dígito). Loopea
                                hasta el siguiente comando.
    #PR{r}G{g}B{b}T{t}          color de ojos RGB. T en décimas de segundo.
                                Corta cualquier motion en curso y congela pose.
    #PS{id}A{ang}T{t}           mueve un servo (id 00-11, ang 000-180).

Motions probados en hardware (grupo-stefi/test.py):
    #M0  home / reset
    #M5  mueve ambos brazos
    #M6  levanta brazo derecho
    #M8  levanta brazo izquierdo
    (#M1/#M2 = caminar: NO se usan, el robot está sobre un basurero)
"""

import os
import time

import serial

DEFAULT_PORT     = os.environ.get("RAPIRO_SERIAL_PORT", "/dev/ttyAMA0")
DEFAULT_BAUD     = int(os.environ.get("RAPIRO_BAUD_RATE", "57600"))
DEFAULT_DURATION = int(os.environ.get("RAPIRO_LED_DURATION_MS", "1000"))


# ---------------------------------------------------------------------------
# Constructores de comandos
# ---------------------------------------------------------------------------

def build_led_command(red: int, green: int, blue: int, duration_ms: int = DEFAULT_DURATION) -> str:
    """Comando de color de ojos RGB.  build_led_command(255,0,0) → '#PR255G000B000T010'."""
    tenths = max(1, int(duration_ms / 100))   # T debe ser > 0 para que el firmware lo aplique
    return f"#PR{red:03d}G{green:03d}B{blue:03d}T{tenths:03d}"


def build_motion_command(n: int) -> str:
    """Comando de motion pre-grabada (0-9, un solo dígito).  build_motion_command(6) → '#M6'."""
    return f"#M{int(n) % 10}"


def build_servo_command(servo_id: int, angle: int, duration_ms: int = 300) -> str:
    """Mueve un servo individual.  build_servo_command(0, 70) → '#PS00A070T003' (cabeza a 70°)."""
    tenths = max(1, int(duration_ms / 100))
    return f"#PS{servo_id:02d}A{angle:03d}T{tenths:03d}"


# ---------------------------------------------------------------------------
# Comportamientos por clase: lista de (comando, espera_segundos)
# Tiempos copiados de test.py (probado en el Rapiro real).
# Cada gesto vuelve a home y termina fijando el color semántico de la clase.
# ---------------------------------------------------------------------------

def build_behavior(clase: str, color: tuple[int, int, int]) -> list[tuple[str, float]]:
    """
    Arma la secuencia de comandos para una clase.

    Devuelve [(comando, espera_s), ...]. El último comando siempre fija el
    color de ojos de la clase (queda "congelado" hasta la próxima clasificación).
    """
    r, g, b = int(color[0]), int(color[1]), int(color[2])
    color_cmd = build_led_command(r, g, b)

    gestos: dict[str, list[tuple[str, float]]] = {
        # Reciclables → gesto de brazo + vuelta a home (#M0)
        "plastico":     [(build_motion_command(6), 1.5), (build_motion_command(0), 1.0)],
        "papel_carton": [(build_motion_command(5), 2.0), (build_motion_command(0), 1.0)],
        "metal":        [(build_motion_command(8), 1.5), (build_motion_command(0), 1.0)],
        # Descarte → sacudir la cabeza ("no", rechazo)
        "descarte_comun": [
            (build_servo_command(0,  70, 300), 0.4),
            (build_servo_command(0, 110, 300), 0.4),
            (build_servo_command(0,  90, 300), 0.4),
        ],
        # Sin identificar → ladear la cabeza (duda)
        "no_identificado": [
            (build_servo_command(0, 75, 500), 0.6),
            (build_servo_command(0, 90, 500), 0.5),
        ],
    }

    secuencia = list(gestos.get(clase, []))
    secuencia.append((color_cmd, 0.3))   # verdict final: color de la clase
    return secuencia


# ---------------------------------------------------------------------------
# Envío serial
# ---------------------------------------------------------------------------

def _enviar_secuencia(frames: list[tuple[str, float]], port: str, baud: int) -> dict:
    """
    Abre el puerto UNA vez, deja 0.5s de settle (igual que test.py), y manda
    cada comando esperando su tiempo. Cierra al final.
    """
    try:
        with serial.Serial(port, baud, timeout=1.0) as ser:
            time.sleep(0.5)   # settle del puerto / boot de la placa
            for cmd, wait in frames:
                ser.write(f"{cmd}\r".encode("ascii"))
                ser.flush()
                time.sleep(wait)
        return {"ok": True, "frames": [c for c, _ in frames], "message": "Secuencia enviada"}
    except serial.SerialException as exc:
        return {"ok": False, "frames": [c for c, _ in frames], "message": str(exc)}


def run_behavior(clase: str, color: tuple[int, int, int],
                 port: str = DEFAULT_PORT, baud: int = DEFAULT_BAUD) -> dict:
    """Ejecuta el comportamiento completo (gesto + color) de una clase en el Rapiro."""
    return _enviar_secuencia(build_behavior(clase, color), port, baud)


def send_led_command(red: int, green: int, blue: int,
                     port: str = DEFAULT_PORT, baud: int = DEFAULT_BAUD,
                     duration_ms: int = DEFAULT_DURATION) -> dict:
    """Solo color de ojos (sin gesto). Útil para tests rápidos."""
    return _enviar_secuencia([(build_led_command(red, green, blue, duration_ms), 0.3)], port, baud)


if __name__ == "__main__":
    # Test rápido: ojos blanco tenue 2s
    print(send_led_command(100, 100, 100, duration_ms=2000))
