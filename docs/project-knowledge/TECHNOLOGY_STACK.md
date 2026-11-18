# Comprehensive Technology Stack Breakdown

---

## 1. Programming Languages & Runtimes

### 1.1 Python (v3.12 / v3.13)
* **Role:** Primary programming language for the ETL engine, database loading scripts, configuration loaders, and automated test suites.
* **Why Selected:** Rich data engineering ecosystem, native bindings for high-performance vectorized libraries (Polars, SQLAlchemy), and concise procedural syntax.
* **Where Used:** `run_pipeline.py`, `etl/*.py`, `core/*.py`, `tests/*.py`.
* **Important Configuration:** Python environment managed via isolated virtual environments (`.venv`) and compiled with `-m py_compile` in CI.
* **Alternatives Considered:** Python was selected over Java/Scala due to lower infrastructure overhead and rapid prototyping speed for university evaluation.

### 1.2 Bash / POSIX Shell
* **Role:** Automation scripting for EC2 lifecycle management, SSH tunnel creation, database backup/restore operations, and CI execution wrappers.
* **Why Selected:** Universally available across Linux environments; zero external runtime dependencies.
* **Where Used:** `scripts/*.sh`, `terraform/user_data.sh`.
* **Important Configuration:** Strict error handling flags (`set -euo pipefail`) in production scripts.

### 1.3 Groovy
* **Role:** Jenkins configuration-as-code scripting and declarative pipeline definition.
* **Why Selected:** Native domain-specific language (DSL) for Jenkins automation.
* **Where Used:** `jenkins/init.groovy.d/01-security.groovy`, `jenkins/init.groovy.d/02-create-job.groovy`, `Jenkinsfile`.

### 1.4 HCL (HashiCorp Configuration Language)
* **Role:** Declarative Infrastructure as Code syntax.
* **Why Selected:** Native syntax for Terraform configurations.
* **Where Used:** `terraform/*.tf`.

---

## 2. Data Engineering & Transformation Libraries

### 2.1 Polars (v1.x)
* **Role:** High-performance, multi-threaded columnar DataFrame library written in Rust.
* **Why Selected:** Memory-efficient stream scanning (`pl.scan_csv`), automatic query optimization (predicate pushdown, projection pushdown), and lightning-fast execution on the multi-gigabyte World Bank CSV dataset without triggering Out-Of-Memory (OOM) errors.
* **Where Used:** `etl/extract.py`, `etl/transform.py`, `etl/load.py`.
* **Integration:** Interacts directly with local CSV files and converts structured batches into database load streams.
* **Alternatives Considered:** **Pandas** was evaluated but rejected due to high memory overhead (~5x memory amplification) and single-threaded execution bottlenecks.

### 2.2 SQLAlchemy (v2.x) & psycopg2-binary
* **Role:** Database abstraction layer, connection pooling, and PostgreSQL wire protocol adapter.
* **Why Selected:** Robust connection lifecycle management, dialect-specific query execution, and high-performance chunked insertion.
* **Where Used:** `etl/load.py`.
* **Important Configuration:** Connects using parameterized connection URLs (`postgresql+psycopg2://user:pass@host:port/dbname`).

### 2.3 uv
* **Role:** Ultra-fast Python package installer and dependency resolver written in Rust.
* **Why Selected:** Instantaneous virtualenv creation and deterministic lockfile generation (`uv.lock`).
* **Where Used:** Local workstation development environment.

---

## 3. Database & Business Intelligence

### 3.1 PostgreSQL (v17.6)
* **Role:** Relational data warehouse storing the analytical star-schema dimensional model.
* **Why Selected:** Enterprise-grade reliability, ACID compliance, advanced indexing (composite B-trees), and native support for large-scale analytical aggregation queries.
* **Where Used:** Cloud EC2 instance and local Docker container (`wdi-db`).
* **Important Configuration:** Runs on port 5432 bound to loopback `127.0.0.1`; data persisted to dedicated Docker volume `wdi_postgres_data`.

### 3.2 Apache Superset (v6.0.0)
* **Role:** Modern, enterprise-ready business intelligence web application and visualization platform.
* **Why Selected:** Native SQL querying against PostgreSQL, rich dashboard component library, automated slice/dashboard serialization, and open-source license.
* **Where Used:** Cloud EC2 instance container (`wdi-superset`).
* **Important Configuration:** Customized via `superset-image/Dockerfile` running strictly as unprivileged user `superset` (UID 1000).

---

## 4. Cloud Infrastructure & Monitoring (AWS)

### 4.1 Terraform (v1.17.x)
* **Role:** Infrastructure as Code engine.
* **Why Selected:** Declarative resource state management, predictable planning (`terraform plan`), provider isolation, and rapid tear-down capabilities.
* **Where Used:** `terraform/main.tf`, `terraform/variables.tf`, `terraform/outputs.tf`.
* **Important Configuration:** Local state file (`terraform.tfstate`) tracked with backup; providers pinned via `.terraform.lock.hcl`.

### 4.2 Amazon Elastic Compute Cloud (EC2)
* **Role:** Compute host for the containerized database and BI server.
* **Configuration:** `m7i-flex.large` (2 vCPUs, 8 GiB RAM, 64-bit x86_64 Nitro architecture), Ubuntu 24.04 LTS.
* **Cost Strategy:** Kept in `stopped` state outside active presentation sessions to prevent idle charges.

### 4.3 Amazon Elastic Block Store (EBS)
* **Role:** Persistent root filesystem and Docker data storage.
* **Configuration:** 40 GiB `gp3` SSD volume, AES-256 server-side encryption enabled (`encrypted = true`), deletion termination protection enabled (`delete_on_termination = false`).

### 4.4 Amazon CloudWatch
* **Role:** Observability, health monitoring, and operational alerting.
* **Components:**
  * **Dashboard:** `WDI-ETL-Monitoring` with 6 widgets tracking CPU, Network, Health Status Checks, and Storage throughput.
  * **Metric Alarm:** `WDI-EC2-HighCPUUtilization` evaluating `CPUUtilization > 80%` over two 5-minute periods with `notBreaching` missing data policy.

---

## 5. CI/CD & Testing Infrastructure

### 5.1 Jenkins LTS (v2.580.x)
* **Role:** Automated Continuous Integration pipeline orchestrator.
* **Why Selected:** Industry-standard enterprise CI/CD engine with declarative pipelines, robust plugin ecosystem (Git, JUnit, Pipeline), and zero cloud hosting costs when running locally.
* **Where Used:** `wdi-jenkins` container on `localhost:8080`.
* **Important Configuration:** Auto-configured on initial startup via Groovy scripts (`01-security.groovy`, `02-create-job.groovy`); uses **Poll SCM** (`H/3 * * * *`) tracking `origin/master`.

### 5.2 Pytest (v9.2.x)
* **Role:** Automated unit testing framework.
* **Why Selected:** Expressive assertion syntax, comprehensive fixture support, and native JUnit XML reporting (`--junitxml`).
* **Where Used:** `tests/test_extract.py`, `tests/test_transform.py`, `tests/test_load.py`.
* **Test Suite:** **12 automated test cases** verifying real transformation logic without mocks.

---

## 6. Containerization & Orchestration

### 6.1 Docker Engine & Docker Compose (v2.x)
* **Role:** Container runtime and multi-container application specification.
* **Why Selected:** Environment parity between development and production, isolated internal network namespaces, and simplified host deployment.
* **Where Used:** `docker-compose.yml`, `jenkins/docker-compose.yml`.
* **Network Isolation:** Internal bridge network `wdi-internal` with no public ingress ports.
