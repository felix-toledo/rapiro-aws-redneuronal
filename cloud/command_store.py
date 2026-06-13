"""
cloud/command_store.py
----------------------
Almacén en memoria del último comando (clase + color) producido por /clasificar.

La Raspberry Pi hace polling a GET /comando para saber a qué color poner los ojos.
Este módulo es el "buzón" entre el clasificador y el actuador de la Pi.

Solo se guarda el ÚLTIMO comando; si la Pi no alcanza a leerlo antes de que
llegue otro, lo descarta (está bien: siempre ejecuta el más reciente).
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from shared.classes import color_para_clase


@dataclass
class Comando:
    """Representa el último resultado de clasificación listo para actuar."""
    clase: str
    color: tuple[int, int, int]
    ts: float = field(default_factory=time.time)   # timestamp UNIX


# ---------------------------------------------------------------------------
# Estado global (singleton de módulo).
# En producción con un solo worker de uvicorn esto es suficiente.
# Si se escala a múltiples workers se necesitaría Redis o similar.
# ---------------------------------------------------------------------------
_ultimo: Optional[Comando] = None


def guardar_comando(clase: str) -> Comando:
    """
    Guarda el último resultado de clasificación.

    Calcula el color a partir de la clase usando shared.classes y lo almacena
    junto con un timestamp UNIX para que la Pi pueda saber si hay algo nuevo.

    Devuelve el Comando generado.
    """
    global _ultimo
    color = color_para_clase(clase)
    _ultimo = Comando(clase=clase, color=color, ts=time.time())
    return _ultimo


def leer_comando() -> Optional[Comando]:
    """
    Devuelve el último Comando almacenado, o None si todavía no se clasificó
    ninguna imagen desde que arrancó el servidor.
    """
    return _ultimo
