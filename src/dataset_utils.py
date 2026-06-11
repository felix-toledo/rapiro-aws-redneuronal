"""
dataset_utils.py
----------------
Utilidades para preparar el dataset de residuos.

Este módulo se encarga de:
1. Reagrupar las clases originales de los datasets en 4 clases finales,
   combinando uno o más datasets de origen.
2. Dividir las imágenes en train / validation / test.
3. Limitar (opcionalmente) la cantidad de imágenes por clase para pruebas rápidas.
4. Validar que el dataset esté completo y mostrar un resumen por clase.
5. Guardar class_indices.json para que las predicciones futuras usen el mismo
   orden de clases que se usó durante el entrenamiento.
6. Cargar los datasets como objetos tf.data listos para entrenar.

Datasets de referencia (se combinan ambos):
- https://www.kaggle.com/datasets/sumn2u/garbage-classification-v2
- https://www.kaggle.com/datasets/joebeachcapital/realwaste
"""

import json
import random
import shutil
from pathlib import Path

import tensorflow as tf

# ---------------------------------------------------------------------------
# Definición de clases
# ---------------------------------------------------------------------------

# Orden FIJO de las clases finales. Este orden define las etiquetas numéricas:
#   0 = plastico, 1 = papel_carton, 2 = metal, 3 = descarte_comun
# Es fundamental usar siempre el mismo orden en entrenamiento e inferencia.
CLASES_FINALES = ["plastico", "papel_carton", "metal", "descarte_comun"]

# Mapeo de las carpetas originales de los datasets a las 4 clases finales.
# Las claves se comparan en minúsculas, así que sirven para:
#   - Garbage Dataset v2 (Kaggle: sumn2u/garbage-classification-v2)
#   - RealWaste (Kaggle: joebeachcapital/realwaste)
#   - Garbage Classification original (Kaggle: mostafaabla/garbage-classification)
#
# IMPORTANTE: "clothes" y "shoes" se excluyen A PROPÓSITO. Sus fotos suelen
# incluir personas (manos, pies, cuerpos), lo que enseñaba a la red que
# "hay piel en la imagen" = descarte_comun, y arruinaba las predicciones
# con la webcam cuando el usuario sostiene el residuo con la mano.
MAPEO_CLASES = {
    # --- plastico ---
    "plastic": "plastico",
    # --- papel_carton ---
    "paper": "papel_carton",
    "cardboard": "papel_carton",
    # --- metal ---
    "metal": "metal",
    # --- descarte_comun: vidrio ---
    "glass": "descarte_comun",
    "green-glass": "descarte_comun",
    "brown-glass": "descarte_comun",
    "white-glass": "descarte_comun",
    # --- descarte_comun: orgánico ---
    "biological": "descarte_comun",
    "food organics": "descarte_comun",
    "vegetation": "descarte_comun",
    # --- descarte_comun: otros ---
    "battery": "descarte_comun",
    "batteries": "descarte_comun",
    "trash": "descarte_comun",
    "miscellaneous trash": "descarte_comun",
    "textile trash": "descarte_comun",
    # --- dataset propio (fotos capturadas con capture_dataset.py) ---
    # Sus carpetas ya usan los nombres finales, por eso el mapeo es directo.
    "plastico": "plastico",
    "papel_carton": "papel_carton",
    "descarte_comun": "descarte_comun",
    # ("metal" ya está mapeado arriba y vale para ambos casos)
}

# Extensiones de imagen aceptadas al recorrer el dataset original.
EXTENSIONES_VALIDAS = {".jpg", ".jpeg", ".png", ".bmp"}

# Si una clase final queda con menos imágenes que este mínimo, se muestra un aviso.
MINIMO_IMAGENES_POR_CLASE = 100


# ---------------------------------------------------------------------------
# Preparación del dataset
# ---------------------------------------------------------------------------

def encontrar_carpeta_clases(raiz):
    """
    Busca, dentro de una descarga de Kaggle, la carpeta que contiene las
    subcarpetas de clases. Cada dataset tiene niveles intermedios distintos,
    así que se localiza la carpeta 'plastic' (presente en todos) y se
    devuelve su carpeta padre.
    """
    raiz = Path(raiz)
    for p in raiz.rglob("*"):
        if p.is_dir() and p.name.lower() == "plastic":
            return p.parent
    raise FileNotFoundError(
        f"No se encontró ninguna carpeta de clases (ej. 'plastic') dentro de {raiz}"
    )


def preparar_dataset(
    dir_origen,
    dir_destino,
    max_imagenes_por_clase=None,
    proporciones=(0.70, 0.15, 0.15),
    seed=42,
):
    """
    Reagrupa uno o más datasets originales en 4 clases y divide en train / val / test.

    Estructura generada en dir_destino:
        train/plastico, train/papel_carton, train/metal, train/descarte_comun
        val/...   (mismas 4 clases)
        test/...  (mismas 4 clases)

    Parámetros:
        dir_origen: carpeta con las clases originales (una subcarpeta por clase),
            o una LISTA de carpetas para combinar varios datasets.
        dir_destino: carpeta donde se creará el dataset reorganizado.
        max_imagenes_por_clase: si se indica, limita cuántas imágenes se usan por
            clase final (útil para una prueba inicial rápida). None = usar todas.
        proporciones: fracciones (train, val, test). Deben sumar 1.0.
        seed: semilla para que el mezclado y la división sean reproducibles.
    """
    # Aceptar una carpeta sola o una lista de carpetas (datasets combinados).
    if isinstance(dir_origen, (str, Path)):
        dir_origen = [dir_origen]
    origenes = [Path(d) for d in dir_origen]
    dir_destino = Path(dir_destino)

    # --- Validaciones básicas ---
    for origen in origenes:
        if not origen.is_dir():
            raise FileNotFoundError(f"No existe la carpeta del dataset original: {origen}")
    if abs(sum(proporciones) - 1.0) > 1e-6:
        raise ValueError(f"Las proporciones {proporciones} deben sumar 1.0")

    # --- Paso 1: recolectar las rutas de imágenes, agrupadas por clase final ---
    imagenes_por_clase = {clase: [] for clase in CLASES_FINALES}
    carpetas_ignoradas = []

    for origen in origenes:
        for carpeta in sorted(origen.iterdir()):
            if not carpeta.is_dir():
                continue
            clase_final = MAPEO_CLASES.get(carpeta.name.lower())
            if clase_final is None:
                # Carpeta que no está en el mapeo: se ignora pero se avisa
                # (clothes y shoes se excluyen a propósito, ver MAPEO_CLASES).
                carpetas_ignoradas.append(carpeta.name)
                continue
            archivos = [
                f for f in carpeta.iterdir()
                if f.is_file() and f.suffix.lower() in EXTENSIONES_VALIDAS
            ]
            if not archivos:
                print(f"AVISO: la carpeta '{carpeta.name}' no contiene imágenes válidas.")
            imagenes_por_clase[clase_final].extend(archivos)

    if carpetas_ignoradas:
        print(f"AVISO: carpetas ignoradas (sin mapeo definido): {carpetas_ignoradas}")

    # Verificar que todas las clases finales tengan imágenes.
    for clase, archivos in imagenes_por_clase.items():
        if not archivos:
            raise RuntimeError(
                f"La clase final '{clase}' quedó sin imágenes. "
                "Revisar la ruta del dataset y el mapeo de clases."
            )

    # --- Paso 2: mezclar, limitar y dividir en train / val / test ---
    # Si la carpeta destino ya existe, se elimina para evitar mezclar ejecuciones.
    if dir_destino.exists():
        shutil.rmtree(dir_destino)

    rng = random.Random(seed)
    frac_train, frac_val, _ = proporciones
    resumen = {}  # clase -> (n_train, n_val, n_test)

    for clase, archivos in imagenes_por_clase.items():
        rng.shuffle(archivos)

        # Limitar la cantidad de imágenes por clase (modo prueba rápida).
        if max_imagenes_por_clase is not None:
            archivos = archivos[:max_imagenes_por_clase]

        n_total = len(archivos)
        n_train = int(n_total * frac_train)
        n_val = int(n_total * frac_val)

        particiones = {
            "train": archivos[:n_train],
            "val": archivos[n_train:n_train + n_val],
            "test": archivos[n_train + n_val:],
        }

        # Copiar cada imagen a su partición. Se renombra con un índice para
        # evitar colisiones de nombres entre las carpetas originales fusionadas.
        for particion, lista in particiones.items():
            carpeta_salida = dir_destino / particion / clase
            carpeta_salida.mkdir(parents=True, exist_ok=True)
            for i, archivo in enumerate(lista):
                shutil.copy2(archivo, carpeta_salida / f"{clase}_{i:05d}{archivo.suffix.lower()}")

        resumen[clase] = (len(particiones["train"]), len(particiones["val"]), len(particiones["test"]))

    # --- Paso 3: mostrar resumen y avisos ---
    print("\nResumen del dataset preparado:")
    print(f"{'Clase':<16} {'Train':>7} {'Val':>7} {'Test':>7} {'Total':>7}")
    for clase in CLASES_FINALES:
        n_train, n_val, n_test = resumen[clase]
        total = n_train + n_val + n_test
        print(f"{clase:<16} {n_train:>7} {n_val:>7} {n_test:>7} {total:>7}")
        if total < MINIMO_IMAGENES_POR_CLASE:
            print(f"  AVISO: '{clase}' tiene pocas imágenes ({total}). "
                  "El modelo puede rendir mal en esta clase.")

    return resumen


# ---------------------------------------------------------------------------
# class_indices.json
# ---------------------------------------------------------------------------

def guardar_class_indices(ruta_salida):
    """
    Guarda el mapeo clase -> índice en un archivo JSON.

    Este archivo se usa luego en la inferencia (imagen individual y webcam)
    para traducir la salida numérica de la red al nombre de la clase,
    garantizando que se use exactamente el mismo orden que en el entrenamiento.
    """
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    class_indices = {clase: indice for indice, clase in enumerate(CLASES_FINALES)}
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(class_indices, f, indent=2, ensure_ascii=False)
    print(f"class_indices guardado en: {ruta_salida} -> {class_indices}")


def cargar_class_indices(ruta):
    """
    Carga class_indices.json y devuelve el mapeo inverso índice -> clase,
    que es el que se necesita para interpretar las predicciones de la red.
    """
    with open(ruta, "r", encoding="utf-8") as f:
        class_indices = json.load(f)
    return {indice: clase for clase, indice in class_indices.items()}


# ---------------------------------------------------------------------------
# Carga de datasets para TensorFlow
# ---------------------------------------------------------------------------

def cargar_datasets(dir_dataset, image_size=(128, 128), batch_size=32, seed=42):
    """
    Carga las carpetas train / val / test como objetos tf.data.Dataset.

    - label_mode="int": las etiquetas son enteros (0 a 3), compatibles con la
      pérdida sparse_categorical_crossentropy.
    - class_names=CLASES_FINALES: fuerza el orden de clases definido en este
      módulo (en lugar del orden alfabético por defecto de Keras).
    - prefetch: prepara el siguiente lote mientras la GPU entrena con el actual.
    """
    dir_dataset = Path(dir_dataset)
    datasets = {}

    for particion in ("train", "val", "test"):
        carpeta = dir_dataset / particion
        if not carpeta.is_dir():
            raise FileNotFoundError(
                f"No existe la carpeta '{carpeta}'. Ejecutar antes preparar_dataset()."
            )
        ds = tf.keras.utils.image_dataset_from_directory(
            carpeta,
            labels="inferred",
            label_mode="int",
            class_names=CLASES_FINALES,
            image_size=image_size,
            batch_size=batch_size,
            shuffle=(particion == "train"),  # solo se mezcla el set de entrenamiento
            seed=seed,
        )
        datasets[particion] = ds.prefetch(tf.data.AUTOTUNE)

    return datasets["train"], datasets["val"], datasets["test"]
