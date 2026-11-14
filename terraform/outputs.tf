output "instance_id" {
  description = "EC2 instance ID used by the start, stop, status, and URL scripts."
  value       = aws_instance.wdi_host.id
}

output "aws_region" {
  description = "AWS region containing the EC2 instance."
  value       = var.aws_region
}

output "instance_type" {
  description = "Selected EC2 instance type."
  value       = aws_instance.wdi_host.instance_type
}

output "dashboard_tunnel_url" {
  description = "Open this URL after starting the SSH tunnel."
  value       = "http://127.0.0.1:8088"
}
