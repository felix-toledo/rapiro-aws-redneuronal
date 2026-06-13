#!/bin/bash
# infra/user_data.sh
# ------------------
# Script de bootstrap para la EC2. Se ejecuta UNA sola vez al primer boot.
# Instala Docker, clona el repo, construye la imagen y levanta la API
# como servicio systemd (se reinicia automáticamente si cae).
#
# Terraform lo pasa como user_data con templatefile(), inyectando:
#   ${repo_url}  — URL del repo GitHub
#   ${api_port}  — Puerto de la API (default 8000)

set -euxo pipefail

# ---------------------------------------------------------------------------
# 1. Sistema: actualizar e instalar Docker + git
# ---------------------------------------------------------------------------
apt-get update -y
apt-get install -y docker.io git

systemctl enable docker
systemctl start docker

# Agregar el usuario ubuntu al grupo docker (para correrlo sin sudo)
usermod -aG docker ubuntu

# ---------------------------------------------------------------------------
# 2. Clonar el repo
# ---------------------------------------------------------------------------
REPO_DIR="/opt/rapiro"
git clone "${repo_url}" "$REPO_DIR"

# ---------------------------------------------------------------------------
# 3. Construir la imagen Docker
# ---------------------------------------------------------------------------
cd "$REPO_DIR"
docker build -f cloud/Dockerfile -t rapiro-api .

# ---------------------------------------------------------------------------
# 4. Crear unidad systemd para que la API arranque automáticamente
# ---------------------------------------------------------------------------
cat > /etc/systemd/system/rapiro-api.service << 'EOF'
[Unit]
Description=Rapiro Clasificador API
After=docker.service
Requires=docker.service

[Service]
Restart=always
RestartSec=5
ExecStartPre=-/usr/bin/docker stop rapiro-api
ExecStartPre=-/usr/bin/docker rm rapiro-api
ExecStart=/usr/bin/docker run \
    --name rapiro-api \
    -p ${api_port}:8000 \
    rapiro-api
ExecStop=/usr/bin/docker stop rapiro-api

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable rapiro-api
systemctl start rapiro-api

echo "=== Bootstrap completo. API arrancando en el puerto ${api_port} ==="
