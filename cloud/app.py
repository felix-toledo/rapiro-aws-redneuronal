"""
cloud/app.py
------------
API FastAPI para el clasificador de residuos Rapiro.

Endpoints:
    POST /clasificar   — recibe imagen, clasifica, guarda el color para la Pi
    GET  /comando      — devuelve el último color (la Pi hace polling aquí)
    GET  /health       — healthcheck básico (¿está el modelo cargado?)

Cómo correr localmente (parado en la carpeta nuestro-codigo/):
    uvicorn cloud.app:app --reload --host 0.0.0.0 --port 8000

En producción (dentro del contenedor Docker):
    CMD ["uvicorn", "cloud.app:app", "--host", "0.0.0.0", "--port", "8000"]
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from cloud import classifier, command_store
from shared.classes import color_para_clase


# ---------------------------------------------------------------------------
# Ciclo de vida: carga el modelo al arrancar el servidor
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga el modelo Keras UNA vez al arrancar uvicorn."""
    print("[app] Cargando modelo...")
    classifier.load_model_once()
    print("[app] Modelo listo. API en línea.")
    yield
    # Cleanup (opcional): liberar memoria al apagar
    print("[app] Apagando servidor.")


# ---------------------------------------------------------------------------
# Aplicación FastAPI
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Rapiro Clasificador de Residuos",
    description=(
        "API cloud-edge para el robot Rapiro.\n\n"
        "La notebook sube una foto y recibe la clase. "
        "La Raspberry Pi hace polling a /comando para mover los LEDs."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: permite que el cliente notebook (o cualquier origen) llame a la API.
# En producción se puede restringir a la IP de la notebook.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/clasificar", summary="Clasificar imagen de residuo")
async def clasificar(imagen: UploadFile = File(..., description="Imagen del residuo (JPEG/PNG)")):
    """
    Recibe una imagen vía multipart/form-data, la clasifica y devuelve:
    - clase        : nombre de la clase predicha
    - confianza    : probabilidad softmax del ganador [0, 1]
    - probabilidades: vector completo de probs por clase
    - color        : [R, G, B] para los ojos del Rapiro

    También guarda el resultado para que la Pi lo lea con GET /comando.
    """
    # Validación básica de tipo MIME (evita subir un PDF por error)
    if imagen.content_type and not imagen.content_type.startswith("image/"):
        raise HTTPException(
            status_code=415,
            detail=f"Tipo de archivo no soportado: {imagen.content_type}. Se esperaba image/*.",
        )

    # Límite de tamaño: 10 MB (evita saturar la EC2)
    MAX_BYTES = 10 * 1024 * 1024
    contenido = await imagen.read()
    if len(contenido) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Imagen demasiado grande ({len(contenido)} bytes). Máximo 10 MB.",
        )

    try:
        clase, confianza, probabilidades = classifier.classify_bytes(contenido)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Guardar el comando para que la Pi lo levante
    cmd = command_store.guardar_comando(clase)
    r, g, b = cmd.color

    return {
        "clase": clase,
        "confianza": round(confianza, 4),
        "probabilidades": {
            nombre: round(probabilidades[idx], 4)
            for idx, nombre in sorted(classifier._indice_a_clase.items())
        },
        "color": [r, g, b],
    }


@app.get("/comando", summary="Obtener último comando para la Pi")
def get_comando():
    """
    Devuelve el último color que debe aplicar la Raspberry Pi a los ojos del Rapiro.

    La Pi hace polling a este endpoint cada ~1 segundo.

    Responde con 204 No Content si todavía no se clasificó ninguna imagen
    (así la Pi sabe que no hay nada que hacer y no pone un color basura).
    """
    cmd = command_store.leer_comando()
    if cmd is None:
        # Sin contenido: la Pi no actúa
        from fastapi.responses import Response
        return Response(status_code=204)

    return {
        "clase": cmd.clase,
        "color": list(cmd.color),
        "ts": cmd.ts,
    }


@app.get("/health", summary="Healthcheck de la API")
def health():
    """
    Healthcheck básico. Docker, systemd y CloudWatch pueden pollear aquí.
    Devuelve 200 si la API está en pie; model_loaded indica si el keras fue cargado.
    """
    return {
        "status": "ok",
        "model_loaded": classifier.model_is_loaded(),
    }
