variable "aws_region"{
    description = "AWS region"
    type = string
    default = "us-east-1"
}

variable "db_username"{
    description = "Master password of RDS"
    type = string
    default = "wdi_user"
}

variable "db_password" {
    description = "Master password of RDS"
    type = string
    default = sensitiive
}

variable "db_name"{AttachementsAttachements
    description = "Database name"
    type = string
    default = "wdi_db"
}