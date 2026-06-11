"""
evaluate.py
-----------
Evaluación del modelo entrenado.

Incluye:
1. Accuracy final en train / validación / test.
2. Matriz de confusión (qué clases se confunden entre sí).
3. Classification report (precision, recall y F1-score por clase).
4. Visualización de imágenes de test con su predicción y clase real.
5. Diagnóstico simple de sobreajuste a partir de las curvas de entrenamiento.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix

from dataset_utils import CLASES_FINALES


def evaluar_accuracy(model, train_ds, val_ds, test_ds):
    """Muestra el accuracy final del modelo en los tres conjuntos."""
    print("Evaluando el modelo en cada conjunto...")
    resultados = {}
    for nombre, ds in (("train", train_ds), ("validación", val_ds), ("test", test_ds)):
        loss, acc = model.evaluate(ds, verbose=0)
        resultados[nombre] = acc
        print(f"  {nombre:<11} -> accuracy: {acc:.4f}  |  loss: {loss:.4f}")
    return resultados


def _predicciones_test(model, test_ds):
    """
    Recorre el dataset de test y devuelve (etiquetas_reales, etiquetas_predichas).
    Se usa internamente para la matriz de confusión y el classification report.
    """
    y_real, y_pred = [], []
    for imagenes, etiquetas in test_ds:
        probabilidades = model.predict(imagenes, verbose=0)
        y_real.extend(etiquetas.numpy())
        y_pred.extend(np.argmax(probabilidades, axis=1))
    return np.array(y_real), np.array(y_pred)


def generar_matriz_confusion(model, test_ds, ruta_salida):
    """
    Calcula y grafica la matriz de confusión sobre el set de test.

    Cada fila es la clase real y cada columna la clase predicha.
    Los valores fuera de la diagonal indican confusiones entre clases.
    """
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    y_real, y_pred = _predicciones_test(model, test_ds)
    matriz = confusion_matrix(y_real, y_pred)

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(matriz, cmap="Blues")
    fig.colorbar(im, ax=ax)

    ax.set_xticks(range(len(CLASES_FINALES)))
    ax.set_yticks(range(len(CLASES_FINALES)))
    ax.set_xticklabels(CLASES_FINALES, rotation=45, ha="right")
    ax.set_yticklabels(CLASES_FINALES)
    ax.set_xlabel("Clase predicha")
    ax.set_ylabel("Clase real")
    ax.set_title("Matriz de confusión (test)")

    # Escribir la cantidad de imágenes en cada celda.
    for i in range(matriz.shape[0]):
        for j in range(matriz.shape[1]):
            color = "white" if matriz[i, j] > matriz.max() / 2 else "black"
            ax.text(j, i, str(matriz[i, j]), ha="center", va="center", color=color)

    fig.tight_layout()
    fig.savefig(ruta_salida, dpi=150)
    plt.show()
    print(f"Matriz de confusión guardada en: {ruta_salida}")

    # Classification report: precision, recall y F1-score por clase.
    # - precision: de lo que predijo como X, cuánto era realmente X.
    # - recall: de todo lo que era X, cuánto detectó.
    # - f1-score: promedio armónico entre precision y recall.
    print("\nClassification report (test):")
    print(classification_report(y_real, y_pred, target_names=CLASES_FINALES, digits=3))


def mostrar_predicciones_ejemplo(model, test_ds, ruta_salida, cantidad=9, umbral=0.60):
    """
    Muestra una grilla de imágenes de test con la clase real y la predicha.

    Aplica la misma regla de confianza que la inferencia real: si la
    probabilidad máxima es menor que el umbral, se muestra "no_identificado".
    Verde = acierto, rojo = error, naranja = no identificado.
    """
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    # Tomar una muestra mezclada de test, para que aparezcan varias clases
    # (el dataset de test se carga ordenado por clase). Las imágenes llegan
    # sin normalizar; la normalización ocurre dentro del modelo (Rescaling).
    muestra = test_ds.unbatch().shuffle(500, seed=1).batch(cantidad)
    imagenes, etiquetas = next(iter(muestra))
    probabilidades = model.predict(imagenes, verbose=0)

    cantidad = min(cantidad, len(imagenes))
    columnas = 3
    filas = int(np.ceil(cantidad / columnas))
    fig, ejes = plt.subplots(filas, columnas, figsize=(4 * columnas, 4 * filas))

    for i, ax in enumerate(np.array(ejes).flatten()):
        if i >= cantidad:
            ax.axis("off")
            continue

        clase_real = CLASES_FINALES[int(etiquetas[i])]
        indice_pred = int(np.argmax(probabilidades[i]))
        confianza = float(probabilidades[i][indice_pred])

        if confianza < umbral:
            clase_pred, color = "no_identificado", "orange"
        else:
            clase_pred = CLASES_FINALES[indice_pred]
            color = "green" if clase_pred == clase_real else "red"

        ax.imshow(imagenes[i].numpy().astype("uint8"))
        ax.set_title(f"Real: {clase_real}\nPred: {clase_pred} ({confianza:.2f})", color=color)
        ax.axis("off")

    fig.tight_layout()
    fig.savefig(ruta_salida, dpi=150)
    plt.show()
    print(f"Ejemplos de predicción guardados en: {ruta_salida}")


def diagnosticar_sobreajuste(history, margen=0.10):
    """
    Diagnóstico simple de sobreajuste comparando train vs validación.

    Si el accuracy de entrenamiento supera al de validación por más que
    'margen' (10% por defecto), el modelo probablemente esté memorizando
    el set de entrenamiento en lugar de generalizar.
    """
    acc_train = history.history["accuracy"][-1]
    acc_val = history.history["val_accuracy"][-1]
    brecha = acc_train - acc_val

    print(f"Accuracy final -> train: {acc_train:.4f} | validación: {acc_val:.4f} "
          f"| brecha: {brecha:.4f}")

    if brecha > margen:
        print("DIAGNÓSTICO: hay indicios de SOBREAJUSTE (la red rinde mucho mejor "
              "en train que en validación).")
        print("Sugerencias: más data augmentation, más Dropout, más imágenes, "
              "o una red más pequeña.")
    elif acc_val < 0.5:
        print("DIAGNÓSTICO: el modelo rinde bajo en validación (subajuste o "
              "datos insuficientes). Probar más épocas, más imágenes por clase "
              "o revisar la calidad del dataset.")
    else:
        print("DIAGNÓSTICO: no se observa sobreajuste importante. "
              "El modelo generaliza razonablemente bien.")
