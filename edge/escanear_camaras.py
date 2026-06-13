"""
edge/escanear_camaras.py
------------------------
Escanea los índices de cámara disponibles (0-9) y muestra cuáles funcionan.
Útil para encontrar el índice de OBS Virtual Camera.

Uso:
    python edge/escanear_camaras.py
"""

import cv2

print("Escaneando cámaras disponibles (índices 0-9)...")
print("-" * 40)

encontradas = []

for i in range(10):
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # CAP_DSHOW es más rápido en Windows
    if cap.isOpened():
        ok, frame = cap.read()
        if ok:
            h, w = frame.shape[:2]
            print(f"  [{i}] ✓ Funciona  ({w}x{h})")
            encontradas.append(i)
        else:
            print(f"  [{i}] ✗ Se abre pero no da frames")
        cap.release()
    else:
        print(f"  [{i}] — No disponible")

print("-" * 40)
if encontradas:
    print(f"Cámaras funcionales: índices {encontradas}")
    print(f"\nPara usar OBS Virtual Camera:")
    print(f"  $env:CAMARA_IDX={encontradas[-1]}; python edge/notebook_client.py")
else:
    print("No se encontró ninguna cámara.")
    print("Usá clasificar_archivos.py para clasificar sin cámara.")
