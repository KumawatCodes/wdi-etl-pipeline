terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_key_pair" "wdi" {
  key_name   = "wdi-superset-admin"
  public_key = file("${path.module}/${var.ssh_public_key_path}")

  tags = {
    Project = "WDI-ETL"
  }
}

resource "aws_security_group" "wdi_host" {
  name        = "wdi-superset-host"
  description = "SSH administration only; Superset is accessed through an SSH tunnel"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH from the administrator current public IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  egress {
    description = "Outbound package, image, and operating system updates"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "wdi-superset-host"
    Project = "WDI-ETL"
  }
}

resource "aws_instance" "wdi_host" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = sort(data.aws_subnets.default.ids)[0]
  vpc_security_group_ids      = [aws_security_group.wdi_host.id]
  key_name                    = aws_key_pair.wdi.key_name
  associate_public_ip_address = true
  user_data                   = file("${path.module}/user_data.sh")

  # Require IMDSv2 and keep the Docker database on encrypted EBS.
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size_gib
    encrypted             = true
    delete_on_termination = false
  }

  disable_api_termination = true

  # lifecycle {
  # prevent_destroy = true
  #}

  tags = {
    Name    = "wdi-superset"
    Project = "WDI-ETL"
  }
}
