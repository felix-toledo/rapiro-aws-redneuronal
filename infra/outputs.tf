# infra/outputs.tf
# -----------------
# Salidas de Terraform que necesitamos al terminar el `apply`.

output "public_ip" {
  description = "IP pública de la EC2. Usarla en API_URL de notebook_client y pi_actuator."
  value       = aws_instance.rapiro_api.public_ip
}

output "public_dns" {
  description = "DNS público de la EC2 (alternativa a la IP)."
  value       = aws_instance.rapiro_api.public_dns
}

output "api_url" {
  description = "URL completa de la API lista para copiar en los clientes."
  value       = "http://${aws_instance.rapiro_api.public_ip}:${var.api_port}"
}

output "ssh_command" {
  description = "Comando SSH para conectarse a la instancia."
  value       = "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_instance.rapiro_api.public_ip}"
}
