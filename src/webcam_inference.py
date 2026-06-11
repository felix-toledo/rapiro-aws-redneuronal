"""
webcam_inference.py
-------------------
Inferencia en tiempo real con una webcam USB.

IMPORTANTE: este script está pensado para ejecutarse en una PC o en una
Raspberry Pi con una webcam USB conectada. NO funciona dentro de Google Colab,
porque Colab corre en un servidor remoto y no tiene acceso directo a la
webcam USB local.

Funcionamiento:
1. Abre la webcam con OpenCV.
2. Toma una región central del frame (donde estaría el residuo frente al robot).
3. DETECCIÓN DE PRESENCIA: compara la región contra una foto del fondo vacío
   (capturada con la tecla 'f'). Solo clasifica cuando detecta que un objeto
   entró al recuadro. Esto evita que la red "clasifique el fondo", porque un
   clasificador no tiene una clase "no hay nada": el softmax siempre reparte
   el 100% entre las clases entrenadas.
4. Si hay objeto, redimensiona la región a 128x128 y la pasa por la CNN.
5. Muestra en pantalla la clase predicha, la confianza, las probabilidades
   de cada clase y la acción futura que ejecutaría el robot Rapiro.

Controles:
    f -> capturar el fondo vacío (hacerlo al inicio, con el recuadro despejado)
    q -> salir

Uso (parado en la carpeta del proyecto, con el modelo ya entrenado):
    python src/webcam_inference.py
"""

import cv2
import numpy as np

from camera_utils import INDICE_CAMARA, extraer_roi_central
from model import IMAGE_SIZE
from predict_image import UMBRAL_CONFIANZA, cargar_modelo_y_clases

# Para no saturar la CPU, se predice una vez cada N frames
# (el video se muestra fluido y la predicción se actualiza varias veces por segundo).
PREDECIR_CADA_N_FRAMES = 5

# Detección de presencia: un píxel se considera "cambiado" si su diferencia
# con el fondo supera DIFERENCIA_PIXEL, y se considera que hay un objeto si
# cambió más del UMBRAL_PRESENCIA (fracción) de la región de interés.
DIFERENCIA_PIXEL = 30
UMBRAL_PRESENCIA = 0.05  # 5% de los píxeles

# Acción futura asociada a cada clase (lo que hará el robot Rapiro).
# Nota: sin acentos, porque cv2.putText solo dibuja caracteres ASCII.
ACCIONES = {
    "plastico": "Enviar a compartimento de plastico",
    "papel_carton": "Enviar a compartimento de papel/carton",
    "metal": "Enviar a compartimento de metal",
    "descarte_comun": "Enviar a compartimento de descarte comun",
    "no_identificado": "Solicitar revision o mantener en descarte",
}


def ejecutar_accion(clase):
    """
    Placeholder para la integración futura con el robot Rapiro.

    En una etapa futura, esta función enviará la orden al Rapiro
    (por ejemplo, por puerto serie hacia su placa controladora) para que
    accione el servomotor que dirige el residuo al compartimento correcto.
    Por ahora no hace nada: la primera etapa del proyecto es solo el modelo.
    """
    pass


def preparar_gris(roi):
    """
    Convierte la ROI a escala de grises y la suaviza.

    El suavizado (blur) hace que la comparación con el fondo sea robusta
    frente al ruido del sensor y pequeñas vibraciones de la cámara.
    """
    gris = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(gris, (21, 21), 0)


def detectar_objeto(roi, fondo_gris):
    """
    Compara la ROI actual contra el fondo vacío capturado.

    Devuelve (hay_objeto, fraccion_cambiada):
    - Se calcula la diferencia absoluta píxel a píxel contra el fondo.
    - Los píxeles que cambiaron más que DIFERENCIA_PIXEL cuentan como "distintos".
    - Si la fracción de píxeles distintos supera UMBRAL_PRESENCIA,
      se considera que un objeto entró al recuadro.
    """
    diferencia = cv2.absdiff(preparar_gris(roi), fondo_gris)
    _, mascara = cv2.threshold(diferencia, DIFERENCIA_PIXEL, 255, cv2.THRESH_BINARY)
    fraccion = np.count_nonzero(mascara) / mascara.size
    return fraccion > UMBRAL_PRESENCIA, fraccion


def predecir_frame(model, indice_a_clase, roi, umbral):
    """
    Clasifica la región de interés de un frame de la webcam.

    OpenCV entrega las imágenes en formato BGR, pero la red fue entrenada con
    imágenes RGB, por lo que primero se convierte el orden de los canales.
    La normalización a [0, 1] la hace la capa Rescaling dentro del modelo.
    """
    rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, IMAGE_SIZE)
    lote = np.expand_dims(rgb.astype("float32"), axis=0)  # (1, 128, 128, 3)

    probabilidades = model.predict(lote, verbose=0)[0]
    indice = int(np.argmax(probabilidades))
    confianza = float(probabilidades[indice])
    clase = indice_a_clase[indice] if confianza >= umbral else "no_identificado"
    return clase, confianza, probabilidades


def main():
    print("Cargando modelo entrenado...")
    model, indice_a_clase = cargar_modelo_y_clases()

    camara = cv2.VideoCapture(INDICE_CAMARA)
    if not camara.isOpened():
        raise RuntimeError(
            f"No se pudo abrir la cámara {INDICE_CAMARA}. "
            "Verificar que la webcam USB esté conectada y probar otro índice."
        )

    print("Webcam iniciada.")
    print("  f -> capturar fondo vacio (hacerlo primero, con el recuadro despejado)")
    print("  q -> salir")

    fondo_gris = None  # foto del fondo vacío (en gris); se captura con 'f'
    contador_frames = 0
    clase, confianza = "no_identificado", 0.0
    probabilidades = np.zeros(len(indice_a_clase))

    while True:
        ok, frame = camara.read()
        if not ok:
            print("No se pudo leer el frame de la cámara.")
            break

        roi, (x1, y1, x2, y2) = extraer_roi_central(frame)

        # --- Detección de presencia ---
        # Sin fondo capturado se clasifica siempre (comportamiento original).
        if fondo_gris is None:
            hay_objeto, fraccion = True, None
        else:
            hay_objeto, fraccion = detectar_objeto(roi, fondo_gris)

        # --- Clasificación (solo si hay objeto, y cada N frames) ---
        if hay_objeto:
            if contador_frames % PREDECIR_CADA_N_FRAMES == 0:
                clase, confianza, probabilidades = predecir_frame(
                    model, indice_a_clase, roi, UMBRAL_CONFIANZA
                )
                ejecutar_accion(clase)  # placeholder: futura orden al Rapiro
        else:
            # Recuadro vacío: no se clasifica nada.
            clase, confianza = "sin_objeto", 0.0
            probabilidades = np.zeros(len(indice_a_clase))
        contador_frames += 1

        # --- Dibujar resultados sobre el frame ---
        if clase == "sin_objeto":
            color, texto_clase = (180, 180, 180), "Esperando objeto..."
            texto_accion = "Colocar un residuo en el recuadro"
        elif clase == "no_identificado":
            color, texto_clase = (0, 165, 255), "Clase: no_identificado"
            texto_accion = f"Accion: {ACCIONES[clase]}"
        else:
            color, texto_clase = (0, 200, 0), f"Clase: {clase}"
            texto_accion = f"Accion: {ACCIONES[clase]}"

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, texto_clase, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(frame, f"Confianza: {confianza:.2f}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(frame, texto_accion, (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Mostrar las 4 probabilidades con una barra, para ver qué "piensa"
        # la red en todo momento (útil para diagnosticar confusiones).
        for i, nombre in sorted(indice_a_clase.items()):
            y_texto = 130 + i * 28
            prob = float(probabilidades[i])
            cv2.putText(frame, f"{nombre:<15} {prob:.2f}", (10, y_texto),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.rectangle(frame, (190, y_texto - 12),
                          (190 + int(prob * 120), y_texto - 2), (255, 255, 255), -1)

        # Estado de la detección de presencia (parte inferior de la pantalla).
        if fondo_gris is None:
            estado = "Fondo NO capturado: presionar 'f' con el recuadro vacio"
        else:
            estado = f"Cambio vs fondo: {fraccion * 100:.0f}% (umbral {UMBRAL_PRESENCIA * 100:.0f}%)"
        cv2.putText(frame, estado, (10, frame.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)

        cv2.imshow("Clasificador de residuos - CNN basica", frame)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla == ord("q"):
            break
        if tecla == ord("f"):
            fondo_gris = preparar_gris(roi)
            print("Fondo capturado. Ahora solo se clasifica cuando hay un objeto.")

    camara.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
