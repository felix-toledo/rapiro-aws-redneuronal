"""
cloud/classifier.py
-------------------
Carga el modelo .keras UNA sola vez al arrancar la API y clasifica imágenes
recibidas como bytes (desde el endpoint POST /clasificar).

El preprocesado replica exactamente lo que hace src/predict_image.py:
  1. Decodificar bytes -> PIL Image (RGB)
  2. Redimensionar a IMAGE_SIZE (128x128)
  3. Convertir a array numpy con forma (1, 128, 128, 3)
  4. Pasar por el modelo (la capa Rescaling interna normaliza a [0, 1])
  5. Aplicar umbral de confianza; si no se supera -> "no_identificado"

Diseño deliberado:
  - La carga del modelo ocurre en load_model_once(), llamada al startup de FastAPI.
  - classify_bytes() es stateless: recibe bytes, devuelve (clase, confianza, probs).
  - Así se puede testear classify_bytes() independientemente de la API.
"""

import io
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

# TensorFlow se importa tarde para no penalizar imports si se testea sin él.
import tensorflow as tf

from shared.classes import CLASES, CLASE_NO_IDENTIFICADO, color_para_clase

# ---------------------------------------------------------------------------
# Rutas (relativas al repo; funciona tanto local como dentro del contenedor)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
RUTA_MODELO = REPO_ROOT / "models" / "garbage_cnn_model.keras"
RUTA_CLASS_INDICES = REPO_ROOT / "outputs" / "class_indices.json"

IMAGE_SIZE = (128, 128)          # debe coincidir con el entrenamiento
UMBRAL_CONFIANZA = 0.60          # por debajo de esto -> no_identificado

# ---------------------------------------------------------------------------
# Estado del módulo (singleton)
# ---------------------------------------------------------------------------
_model: Optional[tf.keras.Model] = None
_indice_a_clase: dict[int, str] = {}


def load_model_once() -> None:
    """
    Carga el modelo Keras y el mapeo índice->clase en memoria.

    Llamar UNA sola vez al arrancar la API (en el evento `startup` de FastAPI).
    Las llamadas posteriores son un no-op gracias al guard `_model is not None`.

    Lanza FileNotFoundError si el .keras no existe (el repo debe incluirlo).
    """
    global _model, _indice_a_clase

    if _model is not None:
        return   # ya cargado

    if not RUTA_MODELO.is_file():
        raise FileNotFoundError(
            f"Modelo no encontrado: {RUTA_MODELO}\n"
            "Asegurate de que 'models/garbage_cnn_model.keras' esté en el repo."
        )

    import json
    _model = tf.keras.models.load_model(str(RUTA_MODELO))

    with open(RUTA_CLASS_INDICES, "r", encoding="utf-8") as f:
        nombre_a_indice: dict[str, int] = json.load(f)

    # Invertimos el dict: {0: "plastico", 1: "papel_carton", ...}
    _indice_a_clase = {v: k for k, v in nombre_a_indice.items()}

    print(f"[classifier] Modelo cargado: {RUTA_MODELO.name}")
    print(f"[classifier] Clases: {_indice_a_clase}")


def model_is_loaded() -> bool:
    """True si el modelo ya está en memoria."""
    return _model is not None


def classify_bytes(image_bytes: bytes) -> tuple[str, float, list[float]]:
    """
    Clasifica una imagen recibida como bytes (JPEG / PNG / etc.).

    Parámetros
    ----------
    image_bytes : bytes
        Contenido crudo del archivo de imagen.

    Devuelve
    --------
    clase : str
        Nombre de la clase predicha, o "no_identificado" si la confianza es baja.
    confianza : float
        Probabilidad softmax de la clase ganadora (valor en [0, 1]).
    probabilidades : list[float]
        Vector completo de probabilidades (una por clase entrenada).

    Lanza
    -----
    RuntimeError si el modelo no fue cargado con load_model_once().
    ValueError si los bytes no se pueden decodificar como imagen.
    """
    if _model is None:
        raise RuntimeError(
            "Modelo no cargado. Llamar load_model_once() antes de clasificar."
        )

    # --- Decodificar y preprocesar ---
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise ValueError(f"No se pudo decodificar la imagen: {exc}") from exc

    img = img.resize(IMAGE_SIZE)                            # (128, 128)
    arr = np.array(img, dtype=np.float32)                  # (128, 128, 3)
    lote = np.expand_dims(arr, axis=0)                     # (1, 128, 128, 3)
    # Nota: NO normalizamos a [0,1] aquí porque la capa Rescaling del modelo
    # lo hace internamente, igual que en el entrenamiento.

    # --- Inferencia ---
    probs = _model.predict(lote, verbose=0)[0]             # (num_clases,)
    indice = int(np.argmax(probs))
    confianza = float(probs[indice])

    # --- Regla de confianza ---
    if confianza >= UMBRAL_CONFIANZA:
        clase = _indice_a_clase.get(indice, CLASE_NO_IDENTIFICADO)
    else:
        clase = CLASE_NO_IDENTIFICADO

    probabilidades = [float(p) for p in probs]
    return clase, confianza, probabilidades
