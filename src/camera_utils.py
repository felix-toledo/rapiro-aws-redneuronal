"""
camera_utils.py
---------------
Utilidades de cámara compartidas entre la inferencia con webcam
(webcam_inference.py) y la captura de fotos propias (capture_dataset.py).
No depende de TensorFlow, así los scripts que solo capturan arrancan rápido.
"""

# Índice de la cámara: 0 suele ser la webcam por defecto.
# Si hay varias cámaras conectadas, probar con 1, 2, etc.
INDICE_CAMARA = 0


def extraer_roi_central(frame):
    """
    Extrae una región central cuadrada del frame (Region Of Interest).

    Se usa la zona central porque el residuo estará ubicado frente a la
    cámara, y así se reduce la influencia del fondo en la predicción.
    Devuelve la ROI y las coordenadas (x1, y1, x2, y2) para dibujarla.
    """
    alto, ancho = frame.shape[:2]
    lado = int(min(alto, ancho) * 0.7)  # cuadrado del 70% del lado menor
    x1 = (ancho - lado) // 2
    y1 = (alto - lado) // 2
    return frame[y1:y1 + lado, x1:x1 + lado], (x1, y1, x1 + lado, y1 + lado)
