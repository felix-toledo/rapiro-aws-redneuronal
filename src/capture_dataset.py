"""
capture_dataset.py
------------------
Captura de fotos propias con la webcam para mejorar el modelo.

Este script permite armar un "dataset propio" con la MISMA cámara, luz y
escena donde funcionará el sistema. Estas fotos se mezclan luego con los
datasets públicos en el entrenamiento (el notebook las toma automáticamente
de la carpeta dataset_propio/), lo que adapta la red al dominio real de uso.

Se guarda solo el recorte central (ROI), que es exactamente lo que ve la red
durante la inferencia con webcam.

Uso (parado en la carpeta del proyecto):
    python src/capture_dataset.py

Controles:
    1 -> guardar foto como plastico
    2 -> guardar foto como papel_carton
    3 -> guardar foto como metal
    4 -> guardar foto como descarte_comun
    q -> salir

Consejos de captura:
    - Apuntar a 50-100 fotos por clase.
    - Variar ángulo, rotación, distancia y posición del objeto entre fotos.
    - Repetir objetos está bien; mejor aún si se agregan objetos distintos.
    - Incluir fotos con el objeto sostenido con la mano Y apoyado.
    - Si es posible, capturar en distintos momentos del día (luz distinta).
"""

import cv2

from pathlib import Path

from camera_utils import INDICE_CAMARA, extraer_roi_central

# Carpeta de salida: dataset_propio/<clase>/ dentro del proyecto.
DIR_SALIDA = Path(__file__).resolve().parent.parent / "dataset_propio"

# Tecla -> clase final (mismo orden que el entrenamiento).
TECLAS_CLASE = {
    ord("1"): "plastico",
    ord("2"): "papel_carton",
    ord("3"): "metal",
    ord("4"): "descarte_comun",
}


def contar_fotos():
    """Devuelve {clase: cantidad de fotos ya guardadas} para mostrar el progreso."""
    return {
        clase: len(list((DIR_SALIDA / clase).glob("*.jpg"))) if (DIR_SALIDA / clase).is_dir() else 0
        for clase in TECLAS_CLASE.values()
    }


def guardar_foto(roi, clase):
    """Guarda la ROI como JPG en dataset_propio/<clase>/ con nombre incremental."""
    carpeta = DIR_SALIDA / clase
    carpeta.mkdir(parents=True, exist_ok=True)
    numero = len(list(carpeta.glob("*.jpg")))
    ruta = carpeta / f"{clase}_propio_{numero:04d}.jpg"
    cv2.imwrite(str(ruta), roi)
    return ruta


def main():
    camara = cv2.VideoCapture(INDICE_CAMARA)
    if not camara.isOpened():
        raise RuntimeError(
            f"No se pudo abrir la cámara {INDICE_CAMARA}. "
            "Verificar que la webcam USB esté conectada y probar otro índice."
        )

    print(f"Captura iniciada. Las fotos se guardan en: {DIR_SALIDA}")
    print("Teclas: 1=plastico  2=papel_carton  3=metal  4=descarte_comun  q=salir")

    contadores = contar_fotos()
    aviso = ""  # último guardado, para mostrarlo en pantalla un instante
    frames_aviso = 0

    while True:
        ok, frame = camara.read()
        if not ok:
            print("No se pudo leer el frame de la cámara.")
            break

        roi, (x1, y1, x2, y2) = extraer_roi_central(frame)

        # Dibujar la ROI y el estado de la captura.
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 200, 0), 2)
        cv2.putText(frame, "1=plastico 2=papel_carton 3=metal 4=descarte q=salir",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        for i, (clase, cantidad) in enumerate(contadores.items()):
            cv2.putText(frame, f"{clase:<15} {cantidad}", (10, 60 + i * 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        if frames_aviso > 0:
            cv2.putText(frame, aviso, (10, frame.shape[0] - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            frames_aviso -= 1

        cv2.imshow("Captura de dataset propio", frame)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla == ord("q"):
            break
        if tecla in TECLAS_CLASE:
            clase = TECLAS_CLASE[tecla]
            ruta = guardar_foto(roi, clase)
            contadores[clase] += 1
            aviso = f"Guardada: {ruta.name}"
            frames_aviso = 20  # mostrar el aviso ~1 segundo
            print(aviso)

    camara.release()
    cv2.destroyAllWindows()

    print("\nResumen de fotos propias:")
    for clase, cantidad in contar_fotos().items():
        print(f"  {clase:<15} {cantidad}")
    print("\nSiguiente paso: subir la carpeta dataset_propio/ a Drive "
          "(dentro de garbage_cnn_project/) y reentrenar en Colab.")


if __name__ == "__main__":
    main()
