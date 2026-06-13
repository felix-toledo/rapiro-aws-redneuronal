# infra/README.md

# Infra — Terraform → AWS EC2

Stack Terraform que levanta la EC2 con la API del Rapiro clasificador.

## Pre-requisitos

1. **Terraform instalado** (`>= 1.5`): https://developer.hashicorp.com/terraform/install  
2. **AWS CLI configurado**:
   ```bash
   aws configure
   # AWS Access Key ID:     <tu key>
   # AWS Secret Access Key: <tu secret>
   # Default region:        us-east-1
   # Output format:         json
   ```
3. **Key pair EC2** creado en la consola de AWS con el nombre `rapiro-key`  
   (o cambiar `var.key_name` en `variables.tf`).
4. **Repo GitHub público** — actualizar `var.repo_url` con tu URL real.

## Pasos

```bash
cd infra/

# Inicializar providers
terraform init

# Ver qué va a crear
terraform plan

# Aplicar (confirmar con "yes")
terraform apply
```

Al terminar, Terraform imprime:
```
api_url     = "http://54.x.x.x:8000"
ssh_command = "ssh -i ~/.ssh/rapiro-key.pem ubuntu@54.x.x.x"
```

## Apuntar los clientes a la EC2

```bash
# notebook_client.py
API_URL=http://54.x.x.x:8000 python edge/notebook_client.py

# pi_actuator.py (en la Pi)
API_URL=http://54.x.x.x:8000 python edge/pi_actuator.py
```

## Apagar la instancia (para no quemar crédito)

```bash
# Detener la instancia (para, no destruye los datos)
aws ec2 stop-instances --instance-ids <instance-id>

# Volver a arrancar
aws ec2 start-instances --instance-ids <instance-id>

# Destruir todo (¡borra los datos!)
terraform destroy
```

## Costo estimado

| Recurso | Costo ~us-east-1 |
|---------|-----------------|
| EC2 t3.medium | $0.0416 / hora ≈ $1/día |
| EBS gp3 20 GB | ~$1.60 / mes |
| CloudWatch logs 7 días | mínimo |

💡 Apagar la instancia cuando no se usa → **$0 mientras está apagada**.
