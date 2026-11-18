# Categorized Operational Command Reference

This document provides a comprehensive, categorized index of all terminal, CLI, and operational commands used across the WDI ETL and Cloud Analytics platform.

---

## 1. Local Development & ETL Commands

| Command | Operational Purpose | Changes Infra? | Safety Rating |
| :--- | :--- | :---: | :---: |
| `python3 run_pipeline.py` | Executes the complete local ETL pipeline (Extract $\to$ Transform $\to$ Load into PostgreSQL). | No | Safe |
| `python3 -m py_compile run_pipeline.py etl/*.py core/*.py` | Performs static bytecode syntax validation across all Python modules. | No | Safe (Read-only) |
| `pytest -v tests/` | Executes the 12 automated unit tests across extraction, casting, and dimensional mapping. | No | Safe (Read-only) |
| `pytest -v --junitxml=reports/test-results.xml tests/` | Runs Pytest suite and exports results in standard JUnit XML format. | No | Safe |

---

## 2. Docker & Container Management Commands

| Command | Operational Purpose | Changes Infra? | Safety Rating |
| :--- | :--- | :---: | :---: |
| `docker compose --env-file .env.example config --quiet` | Validates Compose YAML schema and environment variable completeness. | No | Safe (Read-only) |
| `docker compose up -d` | Starts PostgreSQL (`wdi-db`) and Apache Superset (`wdi-superset`) in detached mode. | No | Operational |
| `docker compose ps` | Displays container health, status, and port bindings. | No | Safe (Read-only) |
| `docker compose logs -f superset` | Tails live application logs from the Apache Superset container. | No | Safe (Read-only) |
| `docker compose down` | Stops and removes active project containers (named volumes are preserved). | No | Operational |
| `docker compose down -v` | **DESTRUCTIVE:** Stops containers and **destroys persistent database volumes**. | No | ⚠️ **DANGEROUS** |

---

## 3. Jenkins CI/CD Orchestration Commands

| Command | Operational Purpose | Changes Infra? | Safety Rating |
| :--- | :--- | :---: | :---: |
| `docker compose -f jenkins/docker-compose.yml up -d` | Launches the local Jenkins LTS controller on `localhost:8080`. | No | Operational |
| `docker compose -f jenkins/docker-compose.yml logs -f` | Inspects Jenkins startup logs, Groovy init scripts, and plugin loading. | No | Safe (Read-only) |
| `curl -s -u "admin:admin123" http://localhost:8080/job/WDI-ETL-Pipeline/api/json` | Queries job details, build history, and health report via the Jenkins REST API. | No | Safe (Read-only) |
| `curl -s -u "admin:admin123" "http://localhost:8080/job/WDI-ETL-Pipeline/lastBuild/consoleText"` | Streams the raw console log of the latest Jenkins pipeline build. | No | Safe (Read-only) |

---

## 4. AWS Infrastructure Management (Terraform & EC2)

| Command | Operational Purpose | Changes Infra? | Safety Rating |
| :--- | :--- | :---: | :---: |
| `terraform -chdir=terraform fmt -check` | Enforces canonical formatting across all `.tf` files. | No | Safe (Read-only) |
| `terraform -chdir=terraform validate` | Validates syntax, attribute names, and provider argument schemas. | No | Safe (Read-only) |
| `terraform -chdir=terraform plan` | Generates an execution plan detailing proposed AWS infrastructure modifications. | No | Safe (Read-only) |
| `terraform -chdir=terraform apply` | **DESTRUCTIVE:** Applies the execution plan to provision or alter live AWS resources. | **YES** | ⚠️ **MODIFIES AWS** |
| `terraform -chdir=terraform destroy` | **DESTRUCTIVE:** Destroys all provisioned AWS cloud resources. | **YES** | 🚨 **HIGH RISK** |
| `aws ec2 start-instances --instance-ids i-079665241b02585f8 --region ap-southeast-2` | Powers on the EC2 host for demonstration or ETL deployment. | State Only | Operational |
| `aws ec2 stop-instances --instance-ids i-079665241b02585f8 --region ap-southeast-2` | Powers down the EC2 host to prevent idle compute costs. | State Only | Operational |

---

## 5. Amazon CloudWatch Observability Commands

| Command | Operational Purpose | Changes Infra? | Safety Rating |
| :--- | :--- | :---: | :---: |
| `aws cloudwatch get-dashboard --dashboard-name WDI-ETL-Monitoring --region ap-southeast-2` | Inspects dashboard JSON structure, metric widgets, and configuration. | No | Safe (Read-only) |
| `aws cloudwatch describe-alarms --alarm-names WDI-EC2-HighCPUUtilization --region ap-southeast-2` | Checks current alarm state (`OK`, `ALARM`, `INSUFFICIENT_DATA`) and evaluation periods. | No | Safe (Read-only) |
| `aws cloudwatch get-metric-statistics ... --namespace AWS/EC2 --metric-name CPUUtilization` | Queries historical 5-minute CPU utilization data points for the EC2 host. | No | Safe (Read-only) |
| `aws cloudwatch list-metrics --namespace CWAgent --region ap-southeast-2` | Lists metrics ingested under the guest operating system namespace. | No | Safe (Read-only) |

---

## 6. Remote Deployment & Operational Shell Scripts

| Command | Operational Purpose | Changes Infra? | Safety Rating |
| :--- | :--- | :---: | :---: |
| `./scripts/instance_info.sh` | Retrieves the EC2 instance ID, public IP, and running state from Terraform & AWS. | No | Safe (Read-only) |
| `./scripts/status.sh` | Queries the operational status of the remote EC2 instance and Docker services. | No | Safe (Read-only) |
| `./scripts/deploy.sh` | Deploys container configurations and triggers remote image builds on the EC2 host. | Host Files | Operational |
| `./scripts/backup_db.sh` | Creates a compressed PostgreSQL custom dump of the production database warehouse. | No | Safe |
| `./scripts/restore_db.sh <DUMP>` | **DESTRUCTIVE:** Overwrites current database state with a previous backup dump. | Database Data | ⚠️ **OVERWRITES DATA** |
| `./scripts/ec2_start.sh` | Wrapper script to power on the AWS EC2 instance. | State Only | Operational |
| `./scripts/ec2_stop.sh` | Wrapper script to cleanly shut down the AWS EC2 instance. | State Only | Operational |
