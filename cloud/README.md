# cloud/README.md

# Cloud — API FastAPI (EC2)

Clasificador de residuos. Corre en Docker sobre una EC2 `t3.medium`.

## Estructura

```
cloud/
├── app.py           # FastAPI: POST /clasificar, GET /comando, GET /health
├── classifier.py    # Carga el modelo .keras y clasifica bytes de imagen
├── command_store.py # "Buzón" en memoria: guarda el último color para la Pi
├── requirements.txt
├── Dockerfile       # (generado en Fase 5)
└── README.md
```

## Correr localmente (sin Docker)

Desde la raíz del repo (`nuestro-codigo/`):

```bash
pip install -r cloud/requirements.txt
uvicorn cloud.app:app --reload --host 0.0.0.0 --port 8000
```

La API queda en `http://localhost:8000`.  
Docs interactivos en `http://localhost:8000/docs`.

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/clasificar` | Recibe imagen (`multipart/form-data`, campo `imagen`), devuelve clase + color RGB |
| `GET`  | `/comando` | Devuelve el último color (la Pi hace polling aquí). 204 si no hay clasificaciones aún |
| `GET`  | `/health` | Healthcheck: `{"status":"ok","model_loaded":true}` |

## Test rápido

```bash
# Health
curl http://localhost:8000/health

# Clasificar imagen de prueba
curl -X POST http://localhost:8000/clasificar \
     -F "imagen=@/ruta/a/foto.jpg"

# Ver el último comando (lo que pollea la Pi)
curl http://localhost:8000/comando
```

## Variables de entorno (opcionales)

No se requieren para correr localmente. En la EC2 las inyecta `user_data.sh`.
