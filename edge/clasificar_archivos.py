"""
edge/clasificar_archivos.py
---------------------------
Clasificador sin cámara: muestra imágenes de una carpeta y las envía a la API.

Uso:
    # Clasificar todas las imágenes de una carpeta:
    python edge/clasificar_archivos.py C:/fotos/basura

    # Clasificar archivos específicos:
    python edge/clasificar_archivos.py foto1.jpg foto2.png

    # Contra EC2:
    API_URL=http://<ip-ec2>:8000 python edge/clasificar_archivos.py C:/fotos

Controles en la ventana:
    ESPACIO / ENTER  →  clasificar imagen actual
    N / →            →  siguiente imagen (sin clasificar)
    P / ←            →  imagen anterior
    Q / ESC          →  salir

Variables de entorno:
    API_URL   URL base de la API (default: http://localhost:8000)
"""

import io
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import requests

# ---------------------------------------------------------------------------
API_URL = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")
ENDPOINT_CLASIFICAR = f"{API_URL}/clasificar"
ENDPOINT_HEALTH     = f"{API_URL}/health"

EXTENSIONES_VALIDAS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

COLOR_TEXTO  = (255, 255, 255)
COLOR_FONDO  = (30, 30, 30)
COLOR_OK     = (0, 200, 100)
COLOR_ERROR  = (50, 50, 255)
COLOR_INFO   = (200, 200, 50)


# ---------------------------------------------------------------------------

def verificar_api() -> bool:
    try:
        resp = requests.get(ENDPOINT_HEALTH, timeout=5)
        data = resp.json()
        if not data.get("model_loaded"):
            print("[WARNING] La API responde pero el modelo no está cargado.")
        print(f"[OK] API en línea: {API_URL}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] No se puede conectar a {API_URL}")
        print("  Corré primero:  uvicorn cloud.app:app --reload")
        return False


def recolectar_imagenes(args: list[str]) -> list[Path]:
    imagenes = []
    for arg in args:
        p = Path(arg)
        if p.is_dir():
            for ext in EXTENSIONES_VALIDAS:
                imagenes.extend(sorted(p.glob(f"*{ext}")))
                imagenes.extend(sorted(p.glob(f"*{ext.upper()}")))
        elif p.is_file() and p.suffix.lower() in EXTENSIONES_VALIDAS:
            imagenes.append(p)
        else:
            print(f"[SKIP] '{arg}' no es una imagen ni carpeta válida.")
    return imagenes


def clasificar_imagen(path: Path) -> dict:
    with open(path, "rb") as f:
        img_bytes = f.read()
    files = {"imagen": (path.name, io.BytesIO(img_bytes), "image/jpeg")}
    resp = requests.post(ENDPOINT_CLASIFICAR, files=files, timeout=30)
    resp.raise_for_status()
    return resp.json()


def dibujar_overlay(frame: np.ndarray, lineas: list[tuple[str, tuple]]) -> np.ndarray:
    """Dibuja varias líneas de texto con fondo en la parte inferior del frame."""
    h, w = frame.shape[:2]
    alto_panel = 30 * len(lineas) + 10
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - alto_panel), (w, h), COLOR_FONDO, -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
    for i, (texto, color) in enumerate(lineas):
        y = h - alto_panel + 25 + i * 30
        cv2.putText(frame, texto, (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
    return frame


def dibujar_contador(frame: np.ndarray, idx: int, total: int, nombre: str) -> np.ndarray:
    """Dibuja contador e índice en la esquina superior izquierda."""
    texto = f"[{idx+1}/{total}] {nombre}"
    cv2.putText(frame, texto, (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, COLOR_INFO, 2, cv2.LINE_AA)
    return frame


def mostrar_resultado(data: dict):
    clase     = data["clase"]
    confianza = data["confianza"]
    color_rgb = data["color"]
    print(f"\n→ Clase:      {clase}")
    print(f"  Confianza:  {confianza:.2%}")
    print(f"  Color ojos: R={color_rgb[0]} G={color_rgb[1]} B={color_rgb[2]}")
    if "probabilidades" in data:
        print("  Probabilidades:")
        for nombre_clase, prob in data["probabilidades"].items():
            barra = "█" * int(prob * 20)
            print(f"    {nombre_clase:<16} {prob:.4f}  {barra}")


# ---------------------------------------------------------------------------

def main():
    args_cli = sys.argv[1:]
    if not args_cli:
        print("Uso: python edge/clasificar_archivos.py <carpeta_o_imagen> [...]")
        print("     python edge/clasificar_archivos.py C:/fotos/basura")
        sys.exit(1)

    imagenes = recolectar_imagenes(args_cli)
    if not imagenes:
        print("[ERROR] No se encontraron imágenes.")
        sys.exit(1)

    print(f"[OK] {len(imagenes)} imagen(es) encontrada(s).")

    if not verificar_api():
        sys.exit(1)

    print("\n=== Clasificador por Archivos ===")
    print("  ESPACIO/ENTER  → clasificar imagen actual")
    print("  N / →          → siguiente")
    print("  P / ←          → anterior")
    print("  Q / ESC        → salir\n")

    idx = 0
    ultimo_resultado: list[tuple[str, tuple]] = [("Presioná ESPACIO para clasificar", COLOR_INFO)]

    while True:
        path_actual = imagenes[idx]
        frame_orig = cv2.imread(str(path_actual))

        if frame_orig is None:
            ultimo_resultado = [(f"No se pudo leer: {path_actual.name}", COLOR_ERROR)]
            frame_orig = np.zeros((400, 600, 3), dtype=np.uint8)

        # Redimensionar para que entre en pantalla manteniendo aspecto
        max_h, max_w = 700, 1000
        h, w = frame_orig.shape[:2]
        escala = min(max_w / w, max_h / h, 1.0)
        if escala < 1.0:
            frame_orig = cv2.resize(frame_orig,
                                    (int(w * escala), int(h * escala)),
                                    interpolation=cv2.INTER_AREA)

        display = frame_orig.copy()
        display = dibujar_contador(display, idx, len(imagenes), path_actual.name)
        display = dibujar_overlay(display, ultimo_resultado)

        cv2.imshow("Clasificador de Imágenes", display)
        key = cv2.waitKey(30) & 0xFF

        if key in (ord("q"), ord("Q"), 27):
            break

        elif key in (ord(" "), 13):  # ESPACIO o ENTER → clasificar
            print(f"\n[INFO] Clasificando: {path_actual.name} ...")
            t0 = time.time()
            try:
                data = clasificar_imagen(path_actual)
                elapsed = time.time() - t0
                mostrar_resultado(data)
                print(f"  Tiempo: {elapsed:.2f}s")

                clase     = data["clase"]
                confianza = data["confianza"]
                color_rgb = data["color"]
                color_bgr = (color_rgb[2], color_rgb[1], color_rgb[0])

                ultimo_resultado = [
                    (f"{clase}  ({confianza:.0%})", color_bgr),
                    (f"R={color_rgb[0]} G={color_rgb[1]} B={color_rgb[2]}", COLOR_TEXTO),
                ]

                # Avanzar automáticamente a la siguiente
                idx = (idx + 1) % len(imagenes)

            except requests.exceptions.HTTPError as exc:
                ultimo_resultado = [(f"Error HTTP {exc.response.status_code}", COLOR_ERROR)]
                print(f"[ERROR] {exc}")
            except requests.exceptions.RequestException as exc:
                ultimo_resultado = [("Sin conexión con la API", COLOR_ERROR)]
                print(f"[ERROR] {exc}")

        elif key in (ord("n"), ord("N"), 83):  # N o flecha derecha
            idx = (idx + 1) % len(imagenes)
            ultimo_resultado = [("Presioná ESPACIO para clasificar", COLOR_INFO)]

        elif key in (ord("p"), ord("P"), 81):  # P o flecha izquierda
            idx = (idx - 1) % len(imagenes)
            ultimo_resultado = [("Presioná ESPACIO para clasificar", COLOR_INFO)]

    cv2.destroyAllWindows()
    print("\n[INFO] Hasta luego.")


if __name__ == "__main__":
    main()
