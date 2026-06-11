"""
train.py
--------
Entrenamiento de la CNN básica.

Incluye:
1. Aplicación de data augmentation SOLO al set de entrenamiento.
2. Callbacks útiles: EarlyStopping, ModelCheckpoint y ReduceLROnPlateau.
3. Gráfico de las curvas de accuracy y loss (train vs validación).
"""

from pathlib import Path

import matplotlib.pyplot as plt
import tensorflow as tf


def entrenar_modelo(model, train_ds, val_ds, augmentation, ruta_modelo, epochs=20):
    """
    Entrena el modelo y guarda la mejor versión en ruta_modelo (.keras).

    Parámetros:
        model: CNN compilada (creada con crear_cnn()).
        train_ds / val_ds: datasets de entrenamiento y validación.
        augmentation: bloque de data augmentation (creado con
            crear_data_augmentation()). Se aplica únicamente a train_ds.
        ruta_modelo: archivo .keras donde guardar el mejor modelo.
        epochs: cantidad máxima de épocas (EarlyStopping puede cortar antes).

    Devuelve el objeto history con la evolución del entrenamiento.
    """
    ruta_modelo = Path(ruta_modelo)
    ruta_modelo.parent.mkdir(parents=True, exist_ok=True)

    # Data augmentation aplicado SOLO a entrenamiento: cada vez que la red ve
    # una imagen, la recibe con una variación aleatoria distinta.
    # Validación y test quedan intactos para medir el rendimiento real.
    train_ds_aug = train_ds.map(
        lambda imagenes, etiquetas: (augmentation(imagenes, training=True), etiquetas),
        num_parallel_calls=tf.data.AUTOTUNE,
    )

    callbacks = [
        # EarlyStopping: si la pérdida de validación no mejora durante
        # 'patience' épocas, detiene el entrenamiento y restaura los mejores
        # pesos. Evita seguir entrenando un modelo que ya no mejora.
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=5,
            restore_best_weights=True,
            verbose=1,
        ),
        # ModelCheckpoint: guarda en disco el modelo cada vez que mejora la
        # pérdida de validación. Así siempre queda la mejor versión guardada.
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(ruta_modelo),
            monitor="val_loss",
            save_best_only=True,
            verbose=1,
        ),
        # ReduceLROnPlateau: si la validación se estanca, reduce la tasa de
        # aprendizaje a la mitad para hacer ajustes más finos de los pesos.
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=3,
            min_lr=1e-6,
            verbose=1,
        ),
    ]

    history = model.fit(
        train_ds_aug,
        validation_data=val_ds,
        epochs=epochs,
        callbacks=callbacks,
    )

    print(f"\nMejor modelo guardado en: {ruta_modelo}")
    return history


def graficar_curvas(history, ruta_salida):
    """
    Grafica accuracy y loss de entrenamiento vs validación y guarda la figura.

    Interpretación rápida:
    - Si ambas curvas de accuracy suben juntas: el modelo está aprendiendo bien.
    - Si train sigue subiendo pero validación se estanca o baja: sobreajuste.
    """
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    epocas = range(1, len(history.history["accuracy"]) + 1)
    fig, (ax_acc, ax_loss) = plt.subplots(1, 2, figsize=(12, 4))

    ax_acc.plot(epocas, history.history["accuracy"], "o-", label="Entrenamiento")
    ax_acc.plot(epocas, history.history["val_accuracy"], "s-", label="Validación")
    ax_acc.set_title("Accuracy por época")
    ax_acc.set_xlabel("Época")
    ax_acc.set_ylabel("Accuracy")
    ax_acc.legend()
    ax_acc.grid(True, alpha=0.3)

    ax_loss.plot(epocas, history.history["loss"], "o-", label="Entrenamiento")
    ax_loss.plot(epocas, history.history["val_loss"], "s-", label="Validación")
    ax_loss.set_title("Loss por época")
    ax_loss.set_xlabel("Época")
    ax_loss.set_ylabel("Loss")
    ax_loss.legend()
    ax_loss.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(ruta_salida, dpi=150)
    plt.show()
    print(f"Curvas de entrenamiento guardadas en: {ruta_salida}")
