# infra/variables.tf
# ------------------
# Variables parametrizables del stack Terraform (EC2 + networking + CloudWatch).
# Cambiar los defaults acá o pasarlos con -var en el apply.

variable "aws_region" {
  description = "Región de AWS donde se despliega la instancia."
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "Tipo de instancia EC2. t3.medium es suficiente para TF-CPU inference."
  type        = string
  default     = "t3.medium"
}

variable "ami_id" {
  description = <<-EOT
    AMI de Ubuntu 22.04 LTS para us-east-1.
    Si cambiás la región, buscá la AMI de Ubuntu 22.04 correspondiente con:
      aws ec2 describe-images --owners 099720109477 \
        --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
        --query 'sort_by(Images,&CreationDate)[-1].ImageId'
  EOT
  type    = string
  default = "ami-0c7217cdde317cfec"   # Ubuntu 22.04 LTS us-east-1 (2024-01)
}

variable "key_name" {
  description = "Nombre del par de claves EC2 para acceso SSH (debe existir en AWS)."
  type        = string
  default     = "rapiro-key"
}

variable "allowed_ssh_cidr" {
  description = "IP/rango desde donde se permite SSH. Usar tu IP pública + /32."
  type        = string
  default     = "0.0.0.0/0"   # ⚠️ Cambiar a tu IP antes del apply en producción
}

variable "api_port" {
  description = "Puerto donde escucha la API FastAPI dentro del contenedor."
  type        = number
  default     = 8000
}

variable "repo_url" {
  description = "URL del repo GitHub público que se clona en user_data.sh."
  type        = string
  default     = "https://github.com/TU-USUARIO/nuestro-codigo.git"   # TODO: actualizar
}

variable "project_name" {
  description = "Prefijo para nombrar los recursos AWS."
  type        = string
  default     = "rapiro"
}
