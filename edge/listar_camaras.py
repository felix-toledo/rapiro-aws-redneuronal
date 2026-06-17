"""
listar_camaras.py
-----------------
Herramienta auxiliar para descubrir qué cámaras tiene la notebook y elegir
el índice correcto para CAMARA_IDX (notebook_client.py) o INDICE_CAMARA
(src/webcam_inference.py).

Uso:
    # Solo listar las cámaras disponibles (sin abrir ventanas):
    python edge/listar_camaras.py

    # Previsualizar las cámaras encontradas (abre una ventana):
    python edge/listar_camaras.py --preview

En la ventana de preview:
    n -> siguiente cámara disponible
    q -> salir
El número de índice se muestra arriba a la izquierda: ese es el valor que
después usás en CAMARA_IDX / INDICE_CAMARA.
"""

import sys

import cv2

# Cuántos índices probar (0..MAX_INDICE-1).
MAX_INDICE = 8

# En Windows, CAP_DSHOW (DirectShow) abre las cámaras mucho más rápido y evita
# los timeouts largos del backend MSMF cuando un índice no existe.
BACKEND = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY


def detectar_camaras():
    """Prueba los índices 0..MAX_INDICE-1 y devuelve los que abren correctamente."""
    disponibles = []
    print(f"Buscando cámaras en los índices 0 a {MAX_INDICE - 1}...\n")
    for idx in range(MAX_INDICE):
        cam = cv2.VideoCapture(idx, BACKEND)
        if cam.isOpened():
            ok, frame = cam.read()
            if ok and frame is not None:
                alto, ancho = frame.shape[:2]
                print(f"  [{idx}] DISPONIBLE  ->  {ancho}x{alto}")
                disponibles.append(idx)
            else:
                print(f"  [{idx}] abre pero no entrega imagen (la salteo)")
        cam.release()

    print()
    if disponibles:
        print(f"Cámaras disponibles: {disponibles}")
        print("Usá ese número en:")
        print("  set CAMARA_IDX=<n>   (notebook_client.py)")
        print("  o INDICE_CAMARA en src/camera_utils.py (webcam_inference.py)")
    else:
        print("No se encontró ninguna cámara. Verificá que esté conectada")
        print("y que ninguna otra app la esté usando.")
    return disponibles


def previsualizar(indices):
    """Muestra en vivo cada cámara; 'n' pasa a la siguiente, 'q' sale."""
    if not indices:
        return
    pos = 0
    while True:
        idx = indices[pos]
        cam = cv2.VideoCapture(idx, BACKEND)
        if not cam.isOpened():
            pos = (pos + 1) % len(indices)
            continue

        print(f"Mostrando cámara [{idx}].  n -> siguiente, q -> salir")
        while True:
            ok, frame = cam.read()
            if not ok:
                break
            cv2.putText(frame, f"Camara indice: {idx}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            cv2.putText(frame, "n = siguiente   q = salir", (10, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.imshow("Previsualizacion de camaras", frame)

            tecla = cv2.waitKey(1) & 0xFF
            if tecla == ord("q"):
                cam.release()
                cv2.destroyAllWindows()
                return
            if tecla == ord("n"):
                break
        cam.release()
        pos = (pos + 1) % len(indices)


if __name__ == "__main__":
    encontradas = detectar_camaras()
    if "--preview" in sys.argv:
        previsualizar(encontradas)
