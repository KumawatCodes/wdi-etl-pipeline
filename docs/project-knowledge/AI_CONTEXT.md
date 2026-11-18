# Master AI Handover Context: WDI ETL & Cloud Analytics Platform

> [!IMPORTANT]
> **PRIMARY HANDOVER DOCUMENT FOR AI ASSISTANTS**  
> This document is a completely self-contained, comprehensive technical specification of the entire project. It is intended to be loaded into the context window of another AI assistant to enable full operational continuity, technical explanations, interview prep, presentation generation, and future code modifications without requiring human intervention.

---

## 1. Project Identity and Objectives

* **Project Title:** World Bank Development Indicators (WDI) Automated ETL, Cloud Data Warehouse & Analytics Platform
* **Primary GitHub Repository:** `https://github.com/KumawatCodes/wdi-etl-pipeline.git` (Branch: `master`)
* **Project Type:** Enterprise-grade Academic Capstone / DevOps, Cloud Architecture & Data Engineering Demonstration
* **Core Objective:** Design, build, deploy, validate, and observe an end-to-end data platform that ingests over six decades of massive multi-gigabyte World Bank global development data, transforms it into an optimized relational star-schema data warehouse, visualizes it via Apache Superset, verifies it through automated Jenkins CI/CD quality gates, and monitors its cloud health using Amazon CloudWatch on AWS.

---

## 2. Project Background & Context

The World Bank's World Development Indicators (WDI) dataset aggregates time-series observations on global poverty, health, education, economic output, and environmental sustainability. 
* **The Raw Data Challenge:** The raw CSV file (`data/raw/WB_WDI.csv`) is **3.6 GB** uncompressed, containing millions of rows with sparse matrix representations, nested metadata, textual code definitions, and missing observation values.
* **The Engineering Goal:** Instead of relying on slow in-memory Python scripts (like default Pandas) or querying raw flat files, this project delivers an enterprise pipeline that:
  1. Utilizes **Polars LazyFrames** with query optimization and predicate pushdowns to stream and clean data without Out-Of-Memory (OOM) errors.
  2. Normalizes records into a **6-dimension Star Schema** in **PostgreSQL 17.6**.
  3. Exposes clean analytical datasets to **Apache Superset 6.0.0** BI dashboards over encrypted, zero-ingress SSH port tunnels.
  4. Manages AWS infrastructure as code using **Terraform v1.17** in AWS Sydney (`ap-southeast-2`).
  5. Implements continuous automated testing and quality gates using **Jenkins LTS** with **GitHub Poll SCM** (`H/3 * * * *`).
  6. Tracks system health and alert states using **Amazon CloudWatch** (`WDI-ETL-Monitoring` dashboard and `WDI-EC2-HighCPUUtilization` alarm).

---

## 3. Complete Technology Stack

| Category | Technology | Version | Operational Purpose & Integration Point |
| :--- | :--- | :--- | :--- |
| **Languages** | Python | 3.12 / 3.13 | Primary language for ETL (`etl/`), logging (`core/`), and tests (`tests/`). |
| | Bash / POSIX Shell | 5.x | Operational automation (`scripts/*.sh`) and EC2 user data bootstrap. |
| | Groovy | 2.x | Jenkins automation (`jenkins/init.groovy.d/`) and declarative `Jenkinsfile`. |
| | HCL | 2.x | Declarative HashiCorp Configuration Language for Terraform (`terraform/*.tf`). |
| **Data Processing** | Polars | 1.x (Rust) | Multi-threaded columnar DataFrame engine; LazyFrame streaming & predicate pushdown. |
| | SQLAlchemy | 2.x | Database connection pooling and object-relational batch streaming. |
| | psycopg2-binary | 2.9.x | High-performance C-optimized PostgreSQL database wire protocol adapter. |
| **Data Warehouse** | PostgreSQL | 17.6 | Analytical relational database housing star schema; containerized in `wdi-db`. |
| **Business Intell.**| Apache Superset | 6.0.0 | Enterprise BI dashboard; containerized in `wdi-superset` (runs as non-root). |
| **CI/CD** | Jenkins LTS | 2.580.x | Continuous integration orchestrator; containerized in `wdi-jenkins` on `localhost:8080`. |
| **Testing** | Pytest | 9.2.x | 12 automated unit/integration tests with JUnit XML reporting (`reports/test-results.xml`). |
| **IaC** | Terraform | 1.17.x | AWS cloud provisioning (VPC, Security Group, SSH Key, EC2 instance, gp3 storage). |
| **Cloud Host** | AWS EC2 | Nitro | `m7i-flex.large` (2 vCPU, 8 GiB RAM, Ubuntu 24.04 LTS) in `ap-southeast-2`. |
| **Cloud Storage** | AWS EBS | gp3 | 40 GiB encrypted SSD volume (`encrypted = true`, `delete_on_termination = false`). |
| **Observability** | Amazon CloudWatch | Service | Real-time dashboard (`WDI-ETL-Monitoring`) and alarm (`WDI-EC2-HighCPUUtilization`). |
| **Containers** | Docker Engine & Compose | 29.x / v2 | Service orchestration, bridge networking (`wdi-internal`), and persistent volumes. |

---

## 4. End-to-End System Architecture

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM ARCHITECTURE OVERVIEW                              │
└────────────────────────────────────────────────────────────────────────────────────────┘

  [DEVELOPER WORKSTATION]
     │
     ├──► git push origin master ──────────► [GITHUB REPOSITORY] (KumawatCodes/wdi-etl-pipeline)
     │                                            │
     │                                            │ (Polled every ~3 min: H/3 * * * *)
     │                                            ▼
     │                                    [JENKINS LTS CONTROLLER] (wdi-jenkins:8080)
     │                                            │
     │                                            ▼ (7-Stage Declarative Quality Gate)
     │                                    1. Checkout SCM
     │                                    2. Environment Check (Python, Terraform, Docker)
     │                                    3. Bytecode Compile (py_compile)
     │                                    4. Automated Testing (12 Pytest tests -> JUnit)
     │                                    5. Terraform Validation (fmt, init, validate)
     │                                    6. Docker Compose & Dockerfile Security Audit
     │                                    7. Final Quality Gate (BUILD SUCCESS)
     │
     ├──► SSH Tunnel (localhost:8088 -> EC2:8088)
     │                                  │
     ▼                                  ▼
  [AWS CLOUD: ap-southeast-2 SYDNEY]
     ┌──────────────────────────────────────────────────────────────────────────────────┐
     │ Security Group: wdi-superset-host (Inbound Port 22 from Operator IP Only)        │
     │                                                                                  │
     │  EC2 Virtual Machine: i-079665241b02585f8 (m7i-flex.large, Ubuntu 24.04 LTS)    │
     │    ├── Docker Internal Network: wdi-internal (bridge)                            │
     │    │     ├── wdi-db (PostgreSQL 17.6) ── Port 127.0.0.1:5432                     │
     │    │     └── wdi-superset (Apache Superset 6.0) ── Port 127.0.0.1:8088           │
     │    │                                                                             │
     │    └── Root Storage: 40 GiB gp3 EBS (AES-256 Encrypted, delete_on_term: false)  │
     │          ├── Named Volume: wdi_postgres_data                                     │
     │          └── Named Volume: wdi_superset_home                                     │
     └──────────────────────────────────┬───────────────────────────────────────────────┘
                                        │
                                        ▼ (Hypervisor Telemetry)
     ┌──────────────────────────────────────────────────────────────────────────────────┐
     │ Amazon CloudWatch Telemetry Engine                                               │
     │    ├── Dashboard: WDI-ETL-Monitoring (6 Widgets: CPU, Net, Health, EBS, Docs)   │
     │    └── Metric Alarm: WDI-EC2-HighCPUUtilization (CPU > 80% for 10 min, State: OK)│
     └──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Component Responsibilities & Module Directory Structure

```text
wdi-etl-pipeline/
├── core/                        # Shared utility modules
│   └── logging.py               # Enterprise logging config (formatters, stdout/file handlers)
├── etl/                         # Data pipeline execution engine
│   ├── extract.py               # Polars LazyFrame reader, indicator whitelist, null filter
│   ├── transform.py             # Column renaming dictionary, strict Int32/Float64 casting
│   └── load.py                  # Dimension builder, surrogate key generator, fact loader
├── sql/                         # Database schema definitions
│   ├── schema_safe.sql          # Non-destructive idempotent warehouse DDL (IF NOT EXISTS)
│   └── schema.sql               # Full teardown/rebuild DDL (DROP TABLE IF EXISTS)
├── superset-image/              # Custom Business Intelligence container definition
│   └── Dockerfile               # Custom image bundling psycopg2-binary, enforcing non-root
├── superset/                    # Superset configuration
│   └── superset_config.py       # Custom metadata database connection, cache, and CSRF rules
├── jenkins/                     # Jenkins LTS CI/CD container configuration
│   ├── Dockerfile               # Bundles Python test suite, Docker CLI, Terraform, plugins
│   ├── docker-compose.yml       # Controller service definition and persistent named volume
│   └── init.groovy.d/           # Automated startup configuration scripts
│       ├── 01-security.groovy   # Admin user creation & matrix authorization
│       └── 02-create-job.groovy # Auto-registration of WDI-ETL-Pipeline SCM polling job
├── terraform/                   # Infrastructure as Code definitions
│   ├── main.tf                  # EC2, Security Group, Key Pair, and encrypted EBS volume
│   ├── variables.tf             # Input parameters (region, instance type, volume size)
│   ├── outputs.tf               # Exported attributes (instance_id, region, tunnel url)
│   └── user_data.sh             # EC2 launch bootstrap script (Docker & Compose setup)
├── monitoring/cloudwatch/       # Observability definitions
│   ├── dashboard.json           # Raw JSON specification for WDI-ETL-Monitoring dashboard
│   ├── iam_cloudwatch_agent_policy.json # Least-privilege IAM policy reference
│   └── amazon-cloudwatch-agent.json     # Guest OS agent configuration template
├── scripts/                     # Operational lifecycle and deployment shell scripts
│   ├── aws_common.sh            # Common helper functions (instance discovery, SSH validation)
│   ├── deploy.sh                # Zero-loss deployment synchronization script
│   ├── backup_db.sh             # Compressed PostgreSQL custom-format dump generator
│   ├── restore_db.sh            # Safe database rollback script
│   ├── init_warehouse_schema.sh # Idempotent schema initialization wrapper
│   ├── ec2_start.sh             # Clean power-on script for the cloud instance
│   └── ec2_stop.sh              # Clean power-off script for budget optimization
├── tests/                       # Automated test suite
│   ├── test_extract.py          # Column lists, indicator whitelist, and null filter tests
│   ├── test_transform.py        # Natural-to-warehouse mapping and type casting tests
│   └── test_load.py             # Dimension builders, key integrity, and fact mapping tests
├── docs/                        # Complete technical documentation suite
│   └── project-knowledge/       # AI handover knowledge directory (13 comprehensive specs)
├── Jenkinsfile                  # Root Declarative CI/CD pipeline definition
├── docker-compose.yml           # Database and Superset container runtime orchestration
├── pyproject.toml               # Python project configuration and dependency specifications
└── run_pipeline.py              # CLI entry point to execute the complete ETL workflow
```

---

## 6. AWS Cloud Infrastructure Deep Dive

* **AWS Account ID:** `529840262552`
* **Region:** `ap-southeast-2` (Sydney)
* **EC2 Instance:** `i-079665241b02585f8` (`m7i-flex.large`, 2 vCPUs, 8.0 GiB RAM)
* **Operating System:** Ubuntu 24.04 LTS (`noble`) AMI `ami-000c0f4df21e3f885`
* **Storage Configuration:**
  - 40 GiB `gp3` root volume encrypted at rest with AWS KMS (`encrypted = true`).
  - Baseline 3,000 IOPS and 125 MiB/s throughput.
  - Termination protection enabled on storage (`delete_on_termination = false`).
* **Security & Network:**
  - Security Group: `wdi-superset-host`.
  - Inbound rules: TCP Port 22 allowed strictly from the operator's current public IP.
  - Zero public ingress for ports 5432 (Postgres) or 8088 (Superset).
  - Outbound rules: `0.0.0.0/0` allowed for OS patches and CloudWatch telemetry.
  - IMDSv2 Enforced (`http_tokens = "required"`).
* **Current Power State:** `stopped` (Preserves student cloud budget when not presenting).

---

## 7. Jenkins CI/CD Pipeline Implementation

* **URL & Access:** `http://localhost:8080` (Credentials: `admin` / `admin123`)
* **Pipeline Script:** Root [Jenkinsfile](file:///home/zenitsu/Data%20%26%20AI/projects/wdi-etl-pipeline/Jenkinsfile)
* **Job Definition:** `WDI-ETL-Pipeline` using `CpsScmFlowDefinition`
* **Source Control Integration:** Git SCM pointing to `https://github.com/KumawatCodes/wdi-etl-pipeline.git`, tracking branch `*/master`.
* **Trigger Strategy:** **Poll SCM** (`H/3 * * * *`). Polls every ~3 minutes; triggers build upon detecting new commit SHAs.
* **The 7 Pipeline Stages:**
  1. **Checkout:** Checks out clean Git repository, logs commit SHA and branch.
  2. **Environment:** Audits Python 3.13, Pytest 9.2, Terraform v1.17, Docker 29.10.
  3. **Validation:** Static compilation (`py_compile`) across all ETL modules; checks required schema/env files.
  4. **Testing:** Executes **12 automated Pytest unit tests**; archives JUnit XML report (`reports/test-results.xml`).
  5. **Terraform Validation:** Formats HCL (`fmt -check`), initializes plugins (`init -backend=false`), validates syntax (`validate`).
  6. **Docker Validation:** Checks Compose syntax (`docker compose config --quiet`) and audits Superset Dockerfile non-root security.
  7. **Final Report:** Emits structured stage audit and quality gate pass status.
* **Latest Verified Build:** Build #6 (**SUCCESS**, triggered automatically via Poll SCM).

---

## 8. Docker & Container Implementation

* **Service `wdi-db` (PostgreSQL 17.6):**
  - Bound to `127.0.0.1:5432`.
  - Health check: `pg_isready -U wdi_admin -d wdi_db`.
  - Volume: `wdi_postgres_data` mounted to `/var/lib/postgresql/data`.
* **Service `wdi-superset` (Apache Superset 6.0.0):**
  - Bound to `127.0.0.1:8088`.
  - Image built from `superset-image/Dockerfile`.
  - Runs as non-root user `superset` (UID 1000).
  - Health check: HTTP GET `/health` on port 8088.
  - Volume: `wdi_superset_home` mounted to `/app/superset_home`.
* **Service `wdi-jenkins` (Jenkins LTS):**
  - Bound to `0.0.0.0:8080` and `50000:50000`.
  - Volume: `wdi-jenkins-ci_jenkins_home` mounted to `/var/jenkins_home`.
  - Mounted `/var/run/docker.sock` to allow agent container operations.

---

## 9. Amazon CloudWatch Implementation Details

* **Dashboard Name:** `WDI-ETL-Monitoring`
* **Dashboard Widgets:**
  1. *EC2 Host CPU Utilization (%):* `AWS/EC2:CPUUtilization` (Average & Maximum). **REAL DATA PRESENT.**
  2. *Network Traffic (In vs Out):* `AWS/EC2:NetworkIn`, `NetworkOut` (Sum). **REAL DATA PRESENT.**
  3. *EC2 Health & Status Checks:* `AWS/EC2:StatusCheckFailed` (Maximum). **REAL DATA PRESENT (0.0 = Healthy).**
  4. *CloudWatch Agent Mem & Disk (%):* `CWAgent:mem_used_percent`, `disk_used_percent`. **EMPTY (Agent uninstalled).**
  5. *EBS Storage I/O Throughput:* `AWS/EC2:EBSReadBytes`, `EBSWriteBytes` (Sum). **REAL DATA PRESENT.**
  6. *Architecture & Reference Summary:* Markdown documentation widget.
* **Metric Alarm:** `WDI-EC2-HighCPUUtilization`
  - Metric: `CPUUtilization` (Namespace: `AWS/EC2`)
  - Threshold: `> 80.0%` for 2 periods of 300 seconds (10 minutes)
  - Missing Data Treatment: `notBreaching`
  - Current State: **`OK`**
  - Actions: `[]` (Empty per authorization guidelines).

---

## 10. Deployment Workflow & Procedures

```text
[Local Machine / CI Pass] ──► ./scripts/backup_db.sh ──► Creates backups/wdi_db-<TS>.dump
                                      │
                                      ▼
                             ./scripts/deploy.sh
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
   1. SSH Sync Assets          2. Docker Build               3. Init Schema
   (compose, DDL to /opt/wdi)  (Superset custom image)       (schema_safe.sql)
                                                                    │
                                                                    ▼
                                                            4. Start Containers
                                                            (docker compose up -d)
```

If an error or corruption occurs:
```bash
./scripts/restore_db.sh backups/wdi_db-<TIMESTAMP>.dump
```

---

## 11. Important Configuration Files & Paths

* **`Jenkinsfile`:** Root declarative CI/CD pipeline script.
* **`docker-compose.yml`:** Production Docker services (Postgres + Superset).
* **`jenkins/docker-compose.yml`:** CI/CD Docker service definition.
* **`jenkins/init.groovy.d/02-create-job.groovy`:** Jenkins job auto-creation and SCM trigger script.
* **`terraform/main.tf`:** Primary AWS cloud infrastructure definition.
* **`sql/schema_safe.sql`:** Idempotent, safe DDL schema initialization script.
* **`monitoring/cloudwatch/dashboard.json`:** JSON definition for the CloudWatch dashboard.
* **`.env.example`:** Sanitized configuration and credential template.

---

## 12. Important Operational Scripts & Purposes

* **`scripts/run_ci_pipeline.sh`:** Standalone shell simulation of the complete 7-stage CI pipeline.
* **`scripts/instance_info.sh`:** Queries Terraform and AWS CLI to output current EC2 IP and power state.
* **`scripts/ec2_start.sh`:** Safely starts the EC2 instance for demo sessions.
* **`scripts/ec2_stop.sh`:** Safely shuts down the EC2 instance to prevent idle cloud costs.
* **`scripts/backup_db.sh`:** Generates verified compressed PostgreSQL custom dumps.
* **`scripts/restore_db.sh`:** Restores the database from a specified dump file.
* **`scripts/deploy.sh`:** Orchestrates remote host file sync, Docker build, and container restart.

---

## 13. Current Project Status

* **ETL Pipeline:** 100% Implemented & Verified.
* **Data Warehouse:** 100% Implemented (Star Schema, B-tree indexes, constraints).
* **Automated Tests:** 100% Passing (12 / 12 Pytest tests).
* **Jenkins CI/CD:** 100% Working (Build #6 SUCCESS via Poll SCM).
* **AWS Cloud Setup:** 100% Defined in Terraform; instance `i-079665241b02585f8` is in `stopped` state.
* **CloudWatch Monitoring:** 100% Active (Dashboard exists with real data; alarm in `OK` state).
* **Guest OS Agent (`CWAgent`):** Reference template only (not installed on host).

---

## 14. Known Limitations & Architecture Boundaries

1. **Continuous Deployment is Decoupled:** Continuous Deployment (CD) is intentionally manual (`scripts/deploy.sh`) to prevent accidental schema corruption or database drops.
2. **CloudWatch Guest OS Telemetry is Inactive:** RAM and partition disk % metrics are not collected because the EC2 instance lacks the CloudWatch Agent and an attached IAM Instance Profile. Hypervisor metrics handle host observability.
3. **Internal Zero-Ingress Network:** Superset and Jenkins are not exposed to the public internet. Access requires an authenticated SSH tunnel (`localhost:8088`).
4. **Alarm Actions are Unconnected:** The CloudWatch alarm has no SNS notification actions configured (`Actions: []`).

---

## 15. Key Troubleshooting & Resolution History

1. **Linux Kernel Shebang Failure:** Paths with spaces (`Data & AI`) broke `.venv/bin/pytest`. Resolved by implementing a dynamic bash wrapper.
2. **Obsolete `pathlib` Backport Crash:** Legacy third-party `pathlib` package conflicted with Python 3.12+ `collections`. Resolved by removing `pathlib>=1.0.1` and using the standard library.
3. **Terraform Provider Cache Failure in CI:** Fresh Git clones lacked cached AWS providers. Resolved by adding `terraform init -backend=false` to Stage 5 of the `Jenkinsfile`.
4. **Jenkins SCM Polling 0ms No-Op:** Pipeline polling evaluated `getLastSuccessfulBuild()`, which was Build #2 with 0 checkouts. Resolved by achieving a successful Git-backed build (Build #5), which unblocked automatic SCM polling for Build #6.
5. **Jenkins REST API 403 Forbidden:** CSRF crumb validation blocked stateless calls. Resolved by implementing cookie jar handling (`-c /tmp/cookies.txt` and `-b /tmp/cookies.txt`).

---

## 16. Security Considerations & Best Practices

* **No Hardcoded Credentials:** All credentials and secrets are managed via environment variables excluded by `.gitignore`.
* **Encrypted Storage:** EBS volume is AES-256 encrypted using AWS KMS.
* **Zero Public Database Exposure:** Ports 5432 and 8088 are bound strictly to `127.0.0.1` inside the EC2 security perimeter.
* **IMDSv2 Enforced:** Guards the EC2 instance against SSRF token theft.
* **Non-Root Containers:** Superset executes under unprivileged UID 1000.

---

## 17. Cost Engineering & Budget Control

* **Stopped Instance Lifecycle:** The EC2 compute instance is kept in `stopped` state outside active presentations, reducing compute fees from ~$74/month to **~$0.50/month**.
* **EBS Storage Only:** While stopped, only the 40 GiB encrypted gp3 volume is billed (~$3.84/month).
* **Zero-Cost CI:** Running Jenkins LTS locally in Docker eliminates the need for a secondary EC2 instance.
* **Total Estimated Cloud Expenditure:** **< $5.00 / month**.

---

## 18. Technical Decisions & Architectural Rationale

* **Why Polars over Pandas?** Polars operates in Rust with multithreaded vectorization, stream scanning, and predicate pushdown. It handles the 3.6 GB dataset without memory exhaustion.
* **Why a Star Schema over 3NF?** Analytical dashboards perform large multi-dimensional aggregations. A star schema minimizes joins and leverages foreign key integer lookups for rapid querying.
* **Why Poll SCM over Webhooks?** Jenkins runs in an internal, non-public Docker environment. Poll SCM allows automated build triggering without exposing local ports via third-party tunnels (ngrok/Cloudflare).
* **Why Decoupled CD?** Enterprise data engineering best practices require operator sign-off and verified database backups before running schema migrations or code deploys against live analytical warehouses.

---

## 19. Future Improvements & Evolution Roadmap

1. **Automated CloudWatch Agent Bootstrap:** Integrate `amazon-cloudwatch-agent` installation into Terraform's `user_data.sh`.
2. **Terraform IAM Module:** Provision `aws_iam_role` and `aws_iam_instance_profile` directly within `terraform/main.tf` to ingest `CWAgent` metrics.
3. **Application Load Balancer (ALB):** Implement an ALB with AWS WAF and HTTPS certificates if public user access is required.
4. **Automated Backups:** Configure AWS Backup for automated daily encrypted EBS volume snapshots.

---

## 20. Essential Command Quick-Reference

```bash
# 1. Run Local Unit Tests
pytest -v tests/

# 2. Check Jenkins SCM Poll Log
curl -s -u "admin:admin123" "http://localhost:8080/job/WDI-ETL-Pipeline/scmPollLog/"

# 3. Start EC2 Instance for Presentation
aws ec2 start-instances --instance-ids i-079665241b02585f8 --region ap-southeast-2

# 4. Stop EC2 Instance to Save Budget
aws ec2 stop-instances --instance-ids i-079665241b02585f8 --region ap-southeast-2

# 5. Open Secure SSH Tunnel to Superset
ssh -i keys/wdi-superset-admin -L 8088:localhost:8088 -N ubuntu@<EC2_PUBLIC_IP>

# 6. Verify CloudWatch Alarm
aws cloudwatch describe-alarms --alarm-names WDI-EC2-HighCPUUtilization --region ap-southeast-2

# 7. Check CloudWatch Dashboard
aws cloudwatch get-dashboard --dashboard-name WDI-ETL-Monitoring --region ap-southeast-2
```

---

## 21. How to Explain This Project in a Technical Interview

When discussing this project with technical recruiters, hiring managers, or evaluators:

1. **The High-Level Elevator Pitch (30 Seconds):**
   > *"I engineered an end-to-end cloud analytics platform for the World Bank's 3.6 GB global development dataset. To solve the memory and query bottlenecks of raw CSVs, I used Polars LazyFrames to extract and clean the data, modeled it into a 6-dimension PostgreSQL star schema, and visualized it in Apache Superset. I provisioned the AWS infrastructure using Terraform in Sydney, automated testing and quality gates through a 7-stage Jenkins CI/CD pipeline integrated with GitHub SCM polling, and established observability with Amazon CloudWatch dashboards and alarms."*

2. **The Deep-Dive Technical Highlights (DevOps / Cloud Focus):**
   - **Infrastructure as Code:** Everything on AWS is codified in Terraform—from Nitro EC2 compute and gp3 encrypted storage to security groups and IMDSv2 enforcement.
   - **CI/CD Quality Engineering:** Every commit pushed to GitHub triggers an automated 7-stage Jenkins pipeline using SCM polling. The pipeline enforces Python compilation, runs 12 Pytest tests, validates Terraform syntax, and audits Docker container configurations.
   - **Security by Design:** Zero open database or BI ports. Superset runs as non-root. Access is routed strictly over authenticated SSH tunnels.
   - **Financial Engineering:** Compute is managed via an on-demand start/stop lifecycle, keeping total cloud costs under $5/month while preserving all EBS warehouse data and CloudWatch telemetry.

---

## 22. Competency Questions Another AI Should Answer from This Context

Any AI assistant loaded with this context file should be able to answer the following questions with zero hallucinations:

1. *What is the exact EC2 instance ID and AWS region?* $\to$ `i-079665241b02585f8` in `ap-southeast-2` (Sydney).
2. *Why was Polars selected instead of Pandas?* $\to$ Polars uses LazyFrame execution graphs, multi-threaded Rust vectorization, and predicate pushdown to process 3.6 GB of data without out-of-memory crashes.
3. *What are the 6 dimensions in the data warehouse?* $\to$ `dim_country`, `dim_indicator`, `dim_date`, `dim_sex`, `dim_age`, and `dim_urbanisation`.
4. *How does Jenkins detect new code changes without webhooks?* $\to$ It uses Poll SCM with schedule `H/3 * * * *`, querying `git ls-remote` on GitHub approximately every 3 minutes.
5. *Why are memory and disk metrics empty on the CloudWatch dashboard?* $\to$ The `amazon-cloudwatch-agent` is not installed on the guest OS, and no IAM instance profile with `cloudwatch:PutMetricData` is attached. Hypervisor metrics (`AWS/EC2`) provide CPU, network, health, and storage telemetry.
6. *What are the parameters of the CloudWatch alarm?* $\to$ Name `WDI-EC2-HighCPUUtilization`, threshold `CPUUtilization > 80%` over two 300-second evaluation periods (10 min), `TreatMissingData: notBreaching`. Current state is `OK`.
7. *How does an operator access the Apache Superset UI?* $\to$ Over an encrypted SSH port tunnel: `ssh -i keys/wdi-superset-admin -L 8088:localhost:8088 -N ubuntu@<IP>`, accessing `http://localhost:8088` locally.
8. *What was the resolution for the Python 3.12 `pathlib` failure?* $\to$ Removed the obsolete third-party PyPI `pathlib` backport from `pyproject.toml` and used Python's native standard library module.
