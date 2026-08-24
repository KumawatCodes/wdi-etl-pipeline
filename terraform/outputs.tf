output "rds_endpoint"{
    description = "RDS  instance rds_endpoint"
    value = aws_db_instance.wdi_postgres.endpoint
}

output "rds_address"{
    description = "RDS hostname"
    value = aws_db_instance.wdi_postgres.address
}

output "rds_port"{
    description = "RDS port"
    value = aws_db_instance.wdi_postgres.port
}

output "rds_username"{
    description = "Master username"
    value = aws_db_instance.wdi_postgres.username
    sensitiive = true
}