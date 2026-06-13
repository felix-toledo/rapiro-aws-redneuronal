"""
shared/classes.py
-----------------
Fuente única de verdad: nombres de clase y mapa de colores (clase -> RGB ojos Rapiro).

Importar desde aquí en cloud/ y edge/ para que los colores sean consistentes
sin repetir la tabla en varios archivos.

Editar los colores SOLO acá; se propagan automáticamente a toda la aplicación.
"""

# Clases que reconoce el modelo (deben coincidir con class_indices.json).
# El orden no importa; el mapeo índice->nombre lo hace el JSON.
CLASES = ["plastico", "papel_carton", "metal", "descarte_comun"]

# Clase especial: la red detectó algo pero la confianza es baja.
# No es una clase entrenada; es una regla aplicada sobre softmax.
CLASE_NO_IDENTIFICADO = "no_identificado"

# ---------------------------------------------------------------------------
# Mapa de colores RGB para los ojos del Rapiro.
# Cada valor es una tupla (R, G, B) con rango [0, 255].
#
# Criterio:
#   plastico       -> amarillo  (color tradicional de contenedor de plástico)
#   papel_carton   -> azul      (color tradicional de contenedor de papel)
#   metal          -> naranja   (color tradicional de contenedor de metal)
#   descarte_comun -> rojo      (residuo general / alerta)
#   no_identificado -> blanco tenue (incertidumbre)
# ---------------------------------------------------------------------------
COLOR_POR_CLASE: dict[str, tuple[int, int, int]] = {
    "plastico":        (255, 255,   0),   # amarillo
    "papel_carton":    (  0,   0, 255),   # azul
    "metal":           (255, 128,   0),   # naranja
    "descarte_comun":  (255,   0,   0),   # rojo
    "no_identificado": ( 40,  40,  40),   # blanco tenue (muy bajo brillo)
}


def color_para_clase(clase: str) -> tuple[int, int, int]:
    """
    Devuelve la tupla RGB para la clase dada.

    Si la clase no está en el mapa (caso inesperado), devuelve el color de
    'no_identificado' para no romper el actuador.

    Ejemplo:
        >>> color_para_clase("plastico")
        (255, 255, 0)
        >>> color_para_clase("desconocida")
        (40, 40, 40)
    """
    return COLOR_POR_CLASE.get(clase, COLOR_POR_CLASE[CLASE_NO_IDENTIFICADO])
