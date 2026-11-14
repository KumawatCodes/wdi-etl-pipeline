variable "aws_region" {
  description = "AWS region for the WDI Superset host."
  type        = string
  default     = "ap-southeast-2"
}

variable "instance_type" {
  description = "EC2 instance type. Check account quota and current offer eligibility before apply."
  type        = string
  default     = "m7i-flex.large"
}

variable "root_volume_size_gib" {
  description = "Encrypted gp3 root EBS volume; Docker volumes and the warehouse persist here."
  type        = number
  default     = 40

  validation {
    condition     = var.root_volume_size_gib >= 40
    error_message = "Use at least 40 GiB for the operating system, Docker images, and WDI data."
  }
}

variable "my_ip_cidr" {
  description = "Administrator public IPv4 CIDR allowed to SSH, e.g. 203.0.113.10/32."
  type        = string
  sensitive   = true

  validation {
    condition     = can(cidrnetmask(var.my_ip_cidr))
    error_message = "my_ip_cidr must be an IPv4 CIDR block, preferably a single-IP /32."
  }
}

variable "ssh_public_key_path" {
  description = "Public SSH key path, relative to the terraform directory. Generate it with scripts/prepare_ssh_key.sh."
  type        = string
  default     = "../keys/wdi-superset-admin.pub"
}

# Kept only so the existing local terraform.tfvars file is accepted while moving
# from the old RDS configuration. It is unused by this EC2-only stack.
