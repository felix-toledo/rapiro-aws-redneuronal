"""
predict_image.py
----------------
Inferencia con una imagen individual.

Carga el modelo entrenado y predice la clase de una imagen. Si la confianza
máxima es menor que el umbral configurado, devuelve "no_identificado".

"no_identificado" NO es una clase entrenada: es una regla de confianza que se
aplica sobre la salida softmax de la red. Esto evita que el sistema tome una
decisión cuando la red "no está segura".

Uso desde la terminal (parado en la carpeta del proyecto):
    python src/predict_image.py ruta/a/la/imagen.jpg
"""

import sys
from pathlib import Path

import numpy as np
import tensorflow as tf

from dataset_utils import cargar_class_indices
from model import IMAGE_SIZE

# Rutas por defecto (relativas a la carpeta del proyecto).
RUTA_MODELO = Path(__file__).resolve().parent.parent / "models" / "garbage_cnn_model.keras"
RUTA_CLASS_INDICES = Path(__file__).resolve().parent.parent / "outputs" / "class_indices.json"

# Umbral de confianza: si la probabilidad máxima es menor, se devuelve
# "no_identificado". Es configurable según qué tan estricto deba ser el sistema.
UMBRAL_CONFIANZA = 0.60


def cargar_modelo_y_clases(ruta_modelo=RUTA_MODELO, ruta_class_indices=RUTA_CLASS_INDICES):
    """
    Carga el modelo entrenado (.keras) y el mapeo índice -> clase.

    Devuelve (model, indice_a_clase). Se carga UNA sola vez y luego se pueden
    hacer muchas predicciones (importante para la webcam y el robot).
    """
    if not Path(ruta_modelo).is_file():
        raise FileNotFoundError(
            f"No se encontró el modelo en '{ruta_modelo}'. "
            "Entrenar primero la red con el notebook de Colab."
        )
    model = tf.keras.models.load_model(ruta_modelo)
    indice_a_clase = cargar_class_indices(ruta_class_indices)
    return model, indice_a_clase


def predict_image(image_path, model, indice_a_clase, umbral=UMBRAL_CONFIANZA):
    """
    Predice la clase de una imagen individual.

    Pasos:
    1. Carga la imagen desde disco.
    2. La redimensiona a 128x128 (el tamaño con el que se entrenó la red).
    3. Le agrega la dimensión de lote (la red espera lotes de imágenes).
       La normalización a [0, 1] la hace la capa Rescaling DENTRO del modelo,
       igual que en el entrenamiento, por eso no se repite acá.
    4. Obtiene las probabilidades softmax y aplica la regla del umbral.

    Devuelve (clase_predicha, confianza, vector_de_probabilidades).
    """
    image_path = Path(image_path)
    if not image_path.is_file():
        raise FileNotFoundError(f"No existe la imagen: {image_path}")

    # Cargar y redimensionar la imagen (Keras la devuelve como RGB).
    imagen = tf.keras.utils.load_img(image_path, target_size=IMAGE_SIZE)
    arreglo = tf.keras.utils.img_to_array(imagen)          # (128, 128, 3)
    lote = np.expand_dims(arreglo, axis=0)                 # (1, 128, 128, 3)

    probabilidades = model.predict(lote, verbose=0)[0]     # vector de 4 valores
    indice = int(np.argmax(probabilidades))
    confianza = float(probabilidades[indice])

    # Regla de confianza: si la red no supera el umbral, no se arriesga.
    clase = indice_a_clase[indice] if confianza >= umbral else "no_identificado"

    return clase, confianza, probabilidades


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python src/predict_image.py ruta/a/la/imagen.jpg")
        sys.exit(1)

    modelo, indice_a_clase = cargar_modelo_y_clases()
    clase, confianza, probabilidades = predict_image(sys.argv[1], modelo, indice_a_clase)

    print("\nPredicción:")
    if clase == "no_identificado":
        print(f"Clase: no_identificado")
        print(f"Confianza máxima: {confianza:.2f} (menor al umbral {UMBRAL_CONFIANZA})")
    else:
        print(f"Clase: {clase}")
        print(f"Confianza: {confianza:.2f}")

    print("\nProbabilidades por clase:")
    for indice, nombre in sorted(indice_a_clase.items()):
        print(f"  {nombre:<16} {probabilidades[indice]:.4f}")
