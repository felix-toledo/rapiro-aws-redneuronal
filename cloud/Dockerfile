# cloud/Dockerfile
# -----------------
# Imagen Docker para la API FastAPI + TensorFlow CPU.
# Se construye con el repo completo porque el modelo vive en models/.
#
# Build (desde la raíz nuestro-codigo/):
#   docker build -f cloud/Dockerfile -t rapiro-api .
#
# Run local:
#   docker run -p 8000:8000 rapiro-api
#
# Run en EC2 (systemd lo hace automáticamente via user_data.sh):
#   docker run -d --restart=always -p 8000:8000 rapiro-api

FROM python:3.11-slim

# Sistema: dependencias mínimas para OpenCV headless y PIL
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar solo lo necesario (reduce capas y tiempo de build)
COPY cloud/requirements.txt /app/cloud/requirements.txt
RUN pip install --no-cache-dir -r /app/cloud/requirements.txt

# Copiar el código fuente y los artefactos del modelo
COPY shared/   /app/shared/
COPY cloud/    /app/cloud/
COPY models/   /app/models/
COPY outputs/  /app/outputs/

# Puerto expuesto
EXPOSE 8000

# Comando de arranque
CMD ["uvicorn", "cloud.app:app", "--host", "0.0.0.0", "--port", "8000"]
