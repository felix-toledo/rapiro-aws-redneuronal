"""
edge/notebook_client.py
-----------------------
Cliente de la notebook: abre la cámara (OpenCV), saca una foto, la envía a la
API de clasificación y muestra el resultado.

Uso:
    # Contra la API local (Fase 2/3):
    python edge/notebook_client.py

    # Contra la EC2 (Fase 6+):
    API_URL=http://<ip-ec2>:8000 python edge/notebook_client.py

Variables de entorno:
    API_URL      URL base de la API (default: http://localhost:8000)
    CAMARA_IDX   Índice de la cámara OpenCV (default: 0)
    GUARDAR_FOTO Si se pone cualquier valor, guarda la foto capturada en disco.

Flujo:
    1. Abre la cámara y muestra preview en una ventana.
    2. Al presionar ESPACIO captura el frame.
    3. Codifica como JPEG en memoria (sin escribir a disco).
    4. Hace POST /clasificar con la imagen.
    5. Muestra la clase y la confianza en la ventana y en la terminal.
    6. Al presionar Q cierra la cámara.
"""

import io
import os
import sys
import time

import cv2
import numpy as np
import requests

# ---------------------------------------------------------------------------
# Configuración vía variables de entorno
# ---------------------------------------------------------------------------
API_URL = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")
CAMARA_IDX = int(os.environ.get("CAMARA_IDX", "0"))
GUARDAR_FOTO = bool(os.environ.get("GUARDAR_FOTO", ""))

ENDPOINT_CLASIFICAR = f"{API_URL}/clasificar"
ENDPOINT_HEALTH     = f"{API_URL}/health"

# Calidad JPEG para la imagen enviada (0-100). 85 es buen balance.
JPEG_QUALITY = 85

# Colores para el texto del overlay (BGR, que es lo que usa OpenCV)
COLOR_TEXTO     = (255, 255, 255)   # blanco
COLOR_FONDO     = (30, 30, 30)      # gris oscuro
COLOR_OK        = (0, 200, 100)     # verde suave
COLOR_ERROR     = (50, 50, 255)     # rojo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def verificar_api() -> bool:
    """Verifica que la API esté en línea antes de arrancar la cámara."""
    try:
        resp = requests.get(ENDPOINT_HEALTH, timeout=5)
        data = resp.json()
        if not data.get("model_loaded"):
            print("[WARNING] La API responde pero el modelo no está cargado.")
        print(f"[OK] API en línea: {API_URL}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] No se puede conectar a {API_URL}")
        print("  Asegurate de que la API esté corriendo:")
        print("  uvicorn cloud.app:app --reload --host 0.0.0.0 --port 8000")
        return False


def frame_a_bytes(frame: np.ndarray) -> bytes:
    """Codifica un frame BGR de OpenCV como bytes JPEG."""
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        raise RuntimeError("No se pudo codificar el frame como JPEG.")
    return buf.tobytes()


def clasificar_frame(frame: np.ndarray) -> dict:
    """
    Envía el frame a la API y devuelve el JSON de respuesta.
    Lanza requests.RequestException si hay error de red.
    """
    img_bytes = frame_a_bytes(frame)
    files = {"imagen": ("captura.jpg", io.BytesIO(img_bytes), "image/jpeg")}
    resp = requests.post(ENDPOINT_CLASIFICAR, files=files, timeout=30)
    resp.raise_for_status()
    return resp.json()


def dibujar_overlay(frame: np.ndarray, texto: str, color: tuple) -> np.ndarray:
    """Dibuja un texto con fondo semitransparente sobre el frame."""
    overlay = frame.copy()
    h, w = frame.shape[:2]
    cv2.rectangle(overlay, (0, h - 60), (w, h), COLOR_FONDO, -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    cv2.putText(
        frame, texto,
        (10, h - 20),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA
    )
    return frame


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not verificar_api():
        sys.exit(1)

    cap = cv2.VideoCapture(CAMARA_IDX)
    if not cap.isOpened():
        print(f"[ERROR] No se pudo abrir la cámara (índice {CAMARA_IDX}).")
        print("  Probá con CAMARA_IDX=1 (o 2) si tenés varias cámaras.")
        sys.exit(1)

    print("\n=== Rapiro Clasificador — Cliente Notebook ===")
    print("  ESPACIO → capturar y clasificar")
    print("  Q       → salir")
    print(f"  API     → {API_URL}\n")

    ultimo_resultado = "Presioná ESPACIO para clasificar"
    ultimo_color = COLOR_TEXTO

    while True:
        ok, frame = cap.read()
        if not ok:
            print("[ERROR] No se pudo leer frame de la cámara.")
            break

        # Dibujar overlay con el último resultado
        display = dibujar_overlay(frame.copy(), ultimo_resultado, ultimo_color)
        cv2.imshow("Rapiro Clasificador", display)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q") or key == ord("Q") or key == 27:   # Q o ESC
            break

        elif key == ord(" "):   # ESPACIO → clasificar
            print("[INFO] Capturando y clasificando...")
            t0 = time.time()

            if GUARDAR_FOTO:
                nombre = f"captura_{int(t0)}.jpg"
                cv2.imwrite(nombre, frame)
                print(f"[INFO] Foto guardada: {nombre}")

            try:
                data = clasificar_frame(frame)
                elapsed = time.time() - t0

                clase = data["clase"]
                confianza = data["confianza"]
                color_rgb = data["color"]   # [R, G, B]

                # OpenCV usa BGR
                ultimo_color = (color_rgb[2], color_rgb[1], color_rgb[0])
                ultimo_resultado = f"{clase}  ({confianza:.0%})"

                print(f"\n→ Clase:      {clase}")
                print(f"  Confianza:  {confianza:.2%}")
                print(f"  Color ojos: R={color_rgb[0]} G={color_rgb[1]} B={color_rgb[2]}")
                print(f"  Tiempo:     {elapsed:.2f}s")
                if "probabilidades" in data:
                    print("  Probabilidades:")
                    for nombre_clase, prob in data["probabilidades"].items():
                        barra = "█" * int(prob * 20)
                        print(f"    {nombre_clase:<16} {prob:.4f}  {barra}")

            except requests.exceptions.HTTPError as exc:
                ultimo_resultado = f"Error HTTP {exc.response.status_code}"
                ultimo_color = COLOR_ERROR
                print(f"[ERROR] {exc}")
            except requests.exceptions.RequestException as exc:
                ultimo_resultado = "Sin conexión con la API"
                ultimo_color = COLOR_ERROR
                print(f"[ERROR] {exc}")

    cap.release()
    cv2.destroyAllWindows()
    print("\n[INFO] Cámara cerrada. Hasta luego.")


if __name__ == "__main__":
    main()
