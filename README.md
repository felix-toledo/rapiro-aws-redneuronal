# Clasificador de residuos con CNN básica (Proyecto Rapiro)

Red neuronal convolucional (CNN) propia, construida capa por capa con TensorFlow/Keras, para clasificar un **residuo individual** presentado frente a una cámara. Es la primera etapa de un proyecto mayor: un robot **Rapiro** ubicado sobre un basurero que observa el residuo con una webcam USB, lo clasifica y lo dirige al compartimento correcto.

En esta etapa **no** se controla el robot ni los servomotores: el objetivo es desarrollar, entrenar, evaluar y dejar listo el modelo de red neuronal.

---

## 1. Objetivo del proyecto

Entrenar una CNN básica capaz de clasificar una imagen de un residuo en una de estas 4 clases:

| Índice | Clase | Ejemplos |
|--------|----------------|----------|
| 0 | `plastico` | botellas, envases plásticos |
| 1 | `papel_carton` | papel, cartón, cajas |
| 2 | `metal` | latas, objetos metálicos |
| 3 | `descarte_comun` | vidrio, orgánico, ropa, calzado, pilas, basura general |

Además existe la respuesta **`no_identificado`**, que **no es una clase entrenada**: es una **regla de confianza**. Si la red predice con una probabilidad máxima menor a un umbral (0.60 por defecto), el sistema responde `no_identificado` en lugar de arriesgar una clasificación dudosa.

## 2. ¿Por qué clasificación de imagen y no detección de objetos?

La detección de objetos (YOLO, etc.) localiza *múltiples* objetos dentro de una escena, con sus cajas delimitadoras. En este sistema, el robot ve **un solo residuo por vez**, ubicado frente a la cámara. No hace falta localizar nada: solo responder "¿qué material es?". La clasificación de imagen es más simple, más liviana, más fácil de explicar y suficiente para el problema.

## 3. ¿Por qué una CNN básica propia?

El proyecto está orientado a **demostrar el funcionamiento de una red neuronal**. Una CNN construida capa por capa permite:

- Mostrar la estructura completa: capas, filtros, neuronas y parámetros.
- Explicar qué aprende cada bloque (bordes → texturas → formas → decisión).
- Ver el proceso de aprendizaje en las curvas de entrenamiento.

Más adelante puede compararse con modelos preentrenados (MobileNetV2, EfficientNetB0, YOLOv8-cls), pero el foco de esta etapa es la CNN propia.

### Explicación conceptual de la red

> El modelo recibe una imagen RGB de 128 × 128 píxeles. Las primeras capas convolucionales extraen patrones visuales simples, como bordes y texturas. Las capas posteriores combinan esos patrones para reconocer formas más complejas asociadas a residuos plásticos, papel/cartón, metales o descarte común. Finalmente, las capas densas integran la información aprendida y la capa softmax entrega una probabilidad para cada clase.

### Arquitectura

```
Entrada (128 x 128 x 3, RGB)
│
├── Rescaling (1/255)            → normaliza los píxeles a [0, 1]
│
├── Conv2D 32 filtros 3x3 + ReLU → detecta bordes y texturas simples
├── MaxPooling2D 2x2             → reduce 128 → 64
│
├── Conv2D 64 filtros 3x3 + ReLU → combina patrones en formas intermedias
├── MaxPooling2D 2x2             → reduce 64 → 32
│
├── Conv2D 128 filtros 3x3 + ReLU → patrones de alto nivel por material
├── MaxPooling2D 2x2             → reduce 32 → 16
│
├── Flatten                      → mapas de características → vector
├── Dense 128 + ReLU             → combina la información para decidir
├── Dropout 0.4                  → apaga neuronas al azar (anti sobreajuste)
└── Dense 4 + softmax            → probabilidades de las 4 clases
```

## 4. Datasets

Se combinan **dos datasets públicos** complementarios (ambos se descargan automáticamente con `kagglehub` en el notebook):

1. **[Garbage Dataset v2](https://www.kaggle.com/datasets/sumn2u/garbage-classification-v2)** (~12.300 imágenes, 10 clases): fotos con **fondos reales y variados** (pisos interiores, suelo exterior, mesas), validadas manualmente. Aporta robustez ante fondos e iluminación distintos a los de un estudio.
2. **[RealWaste](https://www.kaggle.com/datasets/joebeachcapital/realwaste)** (~4.800 imágenes, 9 clases): residuos fotografiados en un **centro de tratamiento real** (Australia) — objetos deformados, sucios y aplastados, tal como se ven los residuos de verdad.

> Notas de selección:
> - Se evaluó inicialmente [Garbage Classification](https://www.kaggle.com/datasets/mostafaabla/garbage-classification) (~15.500 imágenes), pero sus fotos de estudio sobre fondo blanco generalizaban mal a escenas reales con webcam, y sus clases `clothes`/`shoes` (con personas en las fotos) sesgaban al modelo. El mapeo de clases sigue siendo compatible con ese dataset si se quiere comparar.
> - También se evaluaron datasets de Roboflow como [garbage-classifier](https://universe.roboflow.com/student-utr07/garbage-classifier-oehkt), pero están orientados a *detección de objetos*. Como este sistema ve un solo objeto por vez, se eligió *clasificación*.

## 5. Reagrupamiento de clases

Las clases originales de ambos datasets se reagrupan en las 4 clases finales (definido en `src/dataset_utils.py`):

| Clase original | Clase final |
|----------------|-------------|
| plastic | plastico |
| paper, cardboard | papel_carton |
| metal | metal |
| glass, biological, food organics, vegetation, battery, trash, miscellaneous trash, textile trash | descarte_comun |
| clothes, shoes | **excluidas** |

**¿Por qué se excluyen `clothes` y `shoes`?** Sus fotos suelen incluir personas (manos sosteniendo ropa, pies con zapatos). Entrenando con ellas, la red aprendía que "hay piel en la imagen" = `descarte_comun`, y fallaba sistemáticamente con la webcam cuando el usuario sostenía el residuo con la mano. Es un buen ejemplo de cómo un sesgo del dataset se convierte en un sesgo del modelo.

Luego del reagrupamiento, las imágenes se dividen en **70% entrenamiento / 15% validación / 15% prueba**, y el orden de las clases se guarda en `outputs/class_indices.json` para que la inferencia futura use exactamente el mismo orden.

## 6. Estructura del proyecto

```
garbage_cnn_project/
│
├── colab_train_garbage_cnn.ipynb   # notebook principal (Google Colab)
├── requirements.txt                # dependencias para inferencia local
├── README.md
│
├── src/
│   ├── dataset_utils.py            # mapeo de clases, split, class_indices, carga tf.data
│   ├── model.py                    # CNN básica capa por capa + data augmentation
│   ├── train.py                    # entrenamiento, callbacks, curvas
│   ├── evaluate.py                 # accuracy, matriz de confusión, reporte, ejemplos
│   ├── predict_image.py            # inferencia con imagen individual + umbral
│   ├── webcam_inference.py         # inferencia en tiempo real con webcam USB
│   ├── camera_utils.py             # utilidades de cámara compartidas (ROI)
│   └── capture_dataset.py          # captura de fotos propias con la webcam
│
├── dataset_propio/                 # (opcional, se crea con capture_dataset.py)
│   ├── plastico/ ...               # fotos propias por clase, se suman al entrenamiento
│
├── models/                         # (se crea al entrenar)
│   └── garbage_cnn_model.keras
│
└── outputs/                        # (se crea al entrenar)
    ├── class_indices.json
    ├── model_architecture.png
    ├── training_curves.png
    ├── confusion_matrix.png
    └── sample_predictions.png
```

## 7. Cómo entrenar en Google Colab

1. Subir la carpeta `garbage_cnn_project/` completa a Google Drive.
2. Abrir `colab_train_garbage_cnn.ipynb` en Colab.
3. (Recomendado) Activar GPU: *Entorno de ejecución → Cambiar tipo de entorno → GPU*.
4. Ejecutar las celdas en orden. El notebook:
   - Monta Drive e importa los módulos de `src/`.
   - Descarga los dos datasets de Kaggle automáticamente con `kagglehub` (sin credenciales).
   - Reagrupa las clases originales en 4 (excluyendo `clothes`/`shoes`) y divide en train/val/test, mostrando un resumen por clase.
   - Crea la CNN, muestra `model.summary()` y (opcionalmente) el diagrama con `plot_model`.
   - Entrena con data augmentation (solo en train) y callbacks (EarlyStopping, ModelCheckpoint, ReduceLROnPlateau).
   - Grafica curvas, evalúa, genera la matriz de confusión y prueba una imagen.
   - Guarda el mejor modelo en `models/garbage_cnn_model.keras`.

**Cantidad de imágenes (`MAX_IMAGENES_POR_CLASE` en la celda de configuración):**

- `300` → prueba rápida del pipeline (entrena en minutos, pero el modelo resultante casi adivina; no sirve para uso real).
- `2500` → **recomendado** para el entrenamiento real: usa casi todas las imágenes disponibles de `plastico`, `papel_carton` y `metal`, y recorta `descarte_comun` (que junta vidrio, orgánico, pilas y trash) para que las clases queden balanceadas.
- `None` → todo; no recomendado, porque el desbalance hace que la red tienda a responder siempre `descarte_comun`.

**Parámetros principales:** imagen 128×128, `batch_size = 32`, hasta 20 épocas (EarlyStopping puede cortar antes), optimizador Adam, pérdida `sparse_categorical_crossentropy`.

## 8. Cómo evaluar el modelo

El notebook genera:

- **Accuracy en train / validación / test.** El valor de test es la medida más honesta (imágenes nunca vistas).
- **Curvas de accuracy y loss** (`outputs/training_curves.png`).
- **Matriz de confusión** (`outputs/confusion_matrix.png`): cada fila es la clase real y cada columna la predicha; los valores fuera de la diagonal son confusiones.
- **Classification report:** precision, recall y F1-score por clase.
- **Ejemplos visuales** de predicciones sobre test (verde = acierto, rojo = error, naranja = no identificado).
- **Diagnóstico de sobreajuste:** si el accuracy de train supera al de validación por más de un 10%, el modelo probablemente está memorizando en vez de generalizar.

## 9. Cómo probar una imagen individual

En Colab está integrado en el notebook. En una PC local (con el modelo ya entrenado en `models/` y `class_indices.json` en `outputs/`):

```bash
pip install -r requirements.txt
python src/predict_image.py ruta/a/la/imagen.jpg
```

Salida esperada:

```
Predicción:
Clase: plastico
Confianza: 0.87
```

o bien, si la red no está segura:

```
Predicción:
Clase: no_identificado
Confianza máxima: 0.42 (menor al umbral 0.6)
```

El umbral es configurable en `src/predict_image.py` (`UMBRAL_CONFIANZA = 0.60`).

## 10. Cómo usar la webcam USB

> **Importante:** este script se ejecuta en una **PC o Raspberry Pi** con webcam USB conectada. **No funciona dentro de Google Colab**, porque Colab corre en un servidor remoto sin acceso a la webcam local.

```bash
pip install -r requirements.txt
python src/webcam_inference.py
```

El script:

1. Abre la webcam con OpenCV (índice configurable con `INDICE_CAMARA`).
2. Toma la **región central** del frame (donde estará el residuo).
3. **Detección de presencia:** al iniciar, despejar el recuadro y presionar **`f`** para capturar el fondo vacío. A partir de ahí, el sistema solo clasifica cuando detecta que un objeto entró al recuadro (comparación píxel a píxel contra el fondo). Esto evita que la red "clasifique el fondo": un clasificador no tiene clase "no hay nada", el softmax siempre reparte el 100% entre las clases entrenadas.
4. Si hay objeto, la región se redimensiona a 128×128 y se pasa por la CNN.
5. Muestra en pantalla la clase, la confianza, las probabilidades de las 4 clases y la acción futura del robot:

| Clase | Acción futura |
|-------|---------------|
| plastico | Enviar a compartimento de plástico |
| papel_carton | Enviar a compartimento de papel/cartón |
| metal | Enviar a compartimento de metal |
| descarte_comun | Enviar a compartimento de descarte común |
| no_identificado | Solicitar revisión o mantener en descarte |

Controles: **`f`** captura el fondo vacío, **`q`** sale.

## 11. Cómo mejorar el modelo con fotos propias (adaptación de dominio)

Los datasets públicos nunca coinciden exactamente con la cámara, la iluminación y la escena reales de uso. Para cerrar esa brecha, el proyecto incluye un flujo de **fotos propias**:

1. **Capturar** (en la PC, con la webcam conectada):

```bash
python src/capture_dataset.py
```

   Se abre la cámara con el recuadro central. Colocá un residuo y presioná `1` (plastico), `2` (papel_carton), `3` (metal) o `4` (descarte_comun) para guardar la foto del recuadro en `dataset_propio/<clase>/`. Salir con `q`.

2. **Consejos:** apuntar a 50-100 fotos por clase; variar ángulo, rotación, distancia y posición; repetir objetos está bien (mejor si se agregan distintos); incluir fotos con el objeto en mano y apoyado; capturar con distintas luces si es posible.

3. **Reentrenar:** subir la carpeta `dataset_propio/` a Drive (dentro de `garbage_cnn_project/`) y volver a ejecutar el notebook. La carpeta se detecta automáticamente y se suma como tercer origen del dataset combinado.

## 12. Cómo interpretar los resultados

- **Confianza (softmax):** probabilidad que la red asigna a la clase ganadora. 0.90 = muy segura; 0.45 = duda entre clases → `no_identificado`.
- **Accuracy de test alta y brecha train/val pequeña:** el modelo generaliza bien.
- **Matriz de confusión:** si, por ejemplo, `metal` se confunde con `plastico`, conviene revisar/agregar imágenes de esas clases.
- **Recall bajo en una clase:** la red "no encuentra" esa clase; suele indicar pocas imágenes o imágenes poco variadas de esa clase.

## 13. Limitaciones del modelo básico

- Es una **CNN básica**: puede rendir menos que modelos avanzados o preentrenados.
- El rendimiento depende mucho de la **calidad y variedad del dataset**.
- Puede confundirse si la **iluminación** cambia mucho respecto de las fotos de entrenamiento.
- Puede confundirse si el objeto está **muy lejos, parcialmente tapado o con fondo complejo** (el dataset tiene fondos mayormente limpios).
- Para una aplicación real, conviene **agregar imágenes propias** capturadas con la webcam del sistema (mismo encuadre, fondo e iluminación que tendrá el robot) y reentrenar.
- Para una versión avanzada, se puede comparar con **MobileNetV2**, **EfficientNetB0** o **YOLOv8-cls** (transfer learning).

## 14. Proyección a implementación real con Rapiro

Flujo previsto para la etapa final del proyecto:

1. La **webcam** captura una imagen del residuo colocado frente al robot.
2. La **CNN** clasifica el residuo y entrega las probabilidades por clase.
3. El programa decide la clase final aplicando el **umbral de confianza** (si no supera el umbral → `no_identificado`).
4. Según la clase, se envía una **señal al sistema de control** del robot (por ejemplo, por puerto serie hacia la placa controladora del Rapiro).
5. El robot acciona un **servomotor o mecanismo** que direcciona el residuo al compartimento correspondiente del basurero.

En `src/webcam_inference.py` ya existe el punto de integración como función placeholder:

```python
def ejecutar_accion(clase):
    # En una etapa futura, esta función enviará la orden al Rapiro.
    pass
```

Cuando se integre el robot, solo habrá que implementar esta función (por ejemplo, escribiendo el comando correspondiente en el puerto serie), sin modificar el resto del sistema.
