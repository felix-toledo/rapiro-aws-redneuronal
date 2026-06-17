# infra/main.tf
# -------------
# Stack Terraform: EC2 t3.medium + Security Group + IAM Role + CloudWatch.
#
# Antes de aplicar:
#   1. aws configure  (credenciales IAM con permisos EC2 + CloudWatch)
#   2. Crear el key pair "rapiro-key" en la consola o con aws ec2 create-key-pair
#   3. Actualizar var.repo_url con tu repo GitHub real
#   4. Ajustar var.allowed_ssh_cidr a tu IP pública
#   5. terraform init && terraform plan && terraform apply

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.5"
}

provider "aws" {
  region = var.aws_region
}

# ---------------------------------------------------------------------------
# Security Group
# ---------------------------------------------------------------------------
resource "aws_security_group" "rapiro_sg" {
  name        = "${var.project_name}-sg"
  description = "SG para la API del Rapiro clasificador"

  # SSH — solo desde tu IP
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  # API FastAPI — abierto al mundo (la Pi y la notebook la consultan)
  ingress {
    description = "API FastAPI"
    from_port   = var.api_port
    to_port     = var.api_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Salida total
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "${var.project_name}-sg"
    Project = var.project_name
  }
}

# ---------------------------------------------------------------------------
# IAM Role para que la instancia pueda publicar métricas a CloudWatch
# ---------------------------------------------------------------------------
resource "aws_iam_role" "rapiro_role" {
  name = "${var.project_name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })

  tags = { Project = var.project_name }
}

resource "aws_iam_role_policy_attachment" "cloudwatch_agent" {
  role       = aws_iam_role.rapiro_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_instance_profile" "rapiro_profile" {
  name = "${var.project_name}-instance-profile"
  role = aws_iam_role.rapiro_role.name
}

# ---------------------------------------------------------------------------
# EC2 Instance
# ---------------------------------------------------------------------------
resource "aws_instance" "rapiro_api" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.rapiro_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.rapiro_profile.name

  # Bootstrap: instala Docker, clona el repo, build y systemd
  user_data = templatefile("${path.module}/user_data.sh", {
    repo_url = var.repo_url
    api_port = var.api_port
  })

  root_block_device {
    volume_size = 20   # GB — suficiente para Docker + imagen TF-CPU (~4 GB)
    volume_type = "gp3"
  }

  tags = {
    Name    = "${var.project_name}-api"
    Project = var.project_name
  }
}

# ---------------------------------------------------------------------------
# SNS: tópico de alertas + suscripción por email
# ---------------------------------------------------------------------------
# Las alarmas de CloudWatch publican acá, y SNS reenvía el aviso al mail.
# OJO: tras el apply, AWS manda un mail de confirmación a var.alarm_email.
#      HAY QUE HACER CLICK en "Confirm subscription" o no llegan los avisos.
resource "aws_sns_topic" "rapiro_alertas" {
  name = "${var.project_name}-alertas"
  tags = { Project = var.project_name }
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.rapiro_alertas.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# ---------------------------------------------------------------------------
# CloudWatch: Log Group + Alarmas
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "rapiro_logs" {
  name              = "/rapiro/api"
  retention_in_days = 7   # mantener logs 1 semana (no gastar en almacenamiento)
  tags              = { Project = var.project_name }
}

# Alarma 1: CPU alta sostenida (modelo pesado saturando la t3.small)
resource "aws_cloudwatch_metric_alarm" "cpu_alta" {
  alarm_name          = "${var.project_name}-cpu-alta"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 120          # 2 minutos
  statistic           = "Average"
  threshold           = 80           # % de CPU
  alarm_description   = "CPU de la EC2 Rapiro supera el 80% durante 4 minutos"

  # Avisos: dispara mail al entrar en alarma y otro al volver a la normalidad
  alarm_actions = [aws_sns_topic.rapiro_alertas.arn]
  ok_actions    = [aws_sns_topic.rapiro_alertas.arn]

  dimensions = {
    InstanceId = aws_instance.rapiro_api.id
  }

  tags = { Project = var.project_name }
}

# Alarma 2: la instancia falló sus status checks (sistema/instancia caída)
# Esta es la que "llama la atención de verdad": si la EC2 se cuelga, te enterás.
resource "aws_cloudwatch_metric_alarm" "status_check" {
  alarm_name          = "${var.project_name}-status-check-fallido"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 60           # 1 minuto
  statistic           = "Maximum"
  threshold           = 0            # cualquier fallo (>0) dispara
  alarm_description   = "La EC2 Rapiro falló sus status checks 2 min seguidos"

  alarm_actions = [aws_sns_topic.rapiro_alertas.arn]
  ok_actions    = [aws_sns_topic.rapiro_alertas.arn]

  dimensions = {
    InstanceId = aws_instance.rapiro_api.id
  }

  tags = { Project = var.project_name }
}
