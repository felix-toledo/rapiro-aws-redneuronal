"""
model.py
--------
Definición de la CNN básica para clasificación de residuos.

La red se construye manualmente, capa por capa, con TensorFlow/Keras.
El objetivo es que la arquitectura sea clara y explicable: se puede mostrar
qué hace cada capa, cuántos filtros y neuronas tiene, y cómo fluye la
información desde la imagen de entrada hasta las probabilidades de salida.

Arquitectura:
    Entrada: imagen RGB de 128 x 128 x 3
    Rescaling -> normaliza los píxeles de [0, 255] a [0, 1]
    3 bloques convolucionales (Conv2D + MaxPooling2D) con 32, 64 y 128 filtros
    Flatten -> Dense(128, ReLU) -> Dropout(0.4) -> Dense(4, softmax)

Salida (índices de clase):
    0 = plastico, 1 = papel_carton, 2 = metal, 3 = descarte_comun
"""

import tensorflow as tf
from tensorflow.keras import layers, models

# Tamaño de imagen esperado por la red. Debe usarse el mismo valor en
# entrenamiento e inferencia (imagen individual y webcam).
IMAGE_SIZE = (128, 128)


def crear_data_augmentation():
    """
    Crea el bloque de data augmentation (aumento de datos).

    Genera variaciones aleatorias de las imágenes de entrenamiento (espejado,
    rotación, zoom, contraste) para que la red vea "más" ejemplos distintos y
    generalice mejor, en lugar de memorizar las fotos exactas del dataset.

    IMPORTANTE: este bloque se aplica SOLO al set de entrenamiento.
    Validación y test se evalúan con las imágenes originales, sin modificar
    (ver train.py, donde se aplica únicamente a train_ds).
    """
    return tf.keras.Sequential(
        [
            layers.RandomFlip("horizontal"),     # espeja la imagen al azar
            layers.RandomRotation(0.1),          # rota hasta ±10% de vuelta (±36°)
            layers.RandomZoom(0.1),              # acerca/aleja hasta un 10%
            layers.RandomContrast(0.1),          # varía el contraste hasta un 10%
        ],
        name="data_augmentation",
    )


def crear_cnn(num_clases=4, learning_rate=1e-3):
    """
    Construye y compila la CNN básica.

    Devuelve un modelo Keras listo para entrenar con model.fit().
    """
    model = models.Sequential(
        [
            # --- Entrada ---
            # La red recibe imágenes RGB de 128x128 píxeles (3 canales de color).
            layers.Input(shape=(IMAGE_SIZE[0], IMAGE_SIZE[1], 3)),

            # Rescaling: normaliza los píxeles de [0, 255] a [0, 1].
            # Trabajar con valores pequeños y uniformes hace que el
            # entrenamiento sea más estable y rápido. Al estar DENTRO del
            # modelo, la misma normalización se aplica automáticamente en
            # la inferencia (no hay que repetirla a mano).
            layers.Rescaling(1.0 / 255),

            # --- Bloque convolucional 1 ---
            # Conv2D: aprende 32 filtros de 3x3. Cada filtro recorre la imagen
            # y detecta patrones visuales simples: bordes, líneas, texturas.
            # ReLU agrega no linealidad (deja pasar valores positivos y anula
            # los negativos), lo que permite aprender patrones complejos.
            layers.Conv2D(32, (3, 3), activation="relu", padding="same", name="conv1"),
            # MaxPooling2D: reduce el tamaño espacial a la mitad (128 -> 64)
            # quedándose con el valor máximo de cada región de 2x2.
            # Conserva las características más relevantes y reduce el cómputo.
            layers.MaxPooling2D((2, 2), name="pool1"),

            # --- Bloque convolucional 2 ---
            # Con 64 filtros, esta capa combina los patrones simples de la capa
            # anterior para detectar formas intermedias (esquinas, curvas,
            # texturas más elaboradas). Tamaño espacial: 64 -> 32.
            layers.Conv2D(64, (3, 3), activation="relu", padding="same", name="conv2"),
            layers.MaxPooling2D((2, 2), name="pool2"),

            # --- Bloque convolucional 3 ---
            # Con 128 filtros, detecta patrones de alto nivel asociados a cada
            # tipo de residuo: brillo metálico, transparencia del plástico,
            # textura del cartón, etc. Tamaño espacial: 32 -> 16.
            layers.Conv2D(128, (3, 3), activation="relu", padding="same", name="conv3"),
            layers.MaxPooling2D((2, 2), name="pool3"),

            # --- Clasificación ---
            # Flatten: convierte los mapas de características 3D (16x16x128)
            # en un vector 1D de 32768 valores, para conectarlos con las
            # capas densas.
            layers.Flatten(name="flatten"),

            # Dense: 128 neuronas totalmente conectadas. Combina toda la
            # información visual extraída por las convoluciones para "razonar"
            # qué tipo de residuo es.
            layers.Dense(128, activation="relu", name="dense1"),

            # Dropout: durante el entrenamiento apaga al azar el 40% de las
            # neuronas en cada paso. Evita que la red dependa demasiado de
            # neuronas concretas y ayuda a prevenir el sobreajuste.
            layers.Dropout(0.4, name="dropout"),

            # Capa de salida: 4 neuronas, una por clase. Softmax convierte la
            # salida en probabilidades que suman 1 (por ejemplo
            # [0.87, 0.06, 0.04, 0.03] -> 87% de confianza en "plastico").
            layers.Dense(num_clases, activation="softmax", name="salida"),
        ],
        name="cnn_basica_residuos",
    )

    model.compile(
        # Adam: optimizador que ajusta los pesos de la red de forma adaptativa.
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        # sparse_categorical_crossentropy: pérdida adecuada cuando las
        # etiquetas son enteros (0, 1, 2, 3) en vez de vectores one-hot.
        loss="sparse_categorical_crossentropy",
        # accuracy: porcentaje de imágenes clasificadas correctamente.
        metrics=["accuracy"],
    )

    return model
