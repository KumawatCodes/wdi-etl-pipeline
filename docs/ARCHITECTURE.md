# WDI Cloud Architecture & System Design

## 1. End-to-End System Architecture

The WDI Analytics platform consists of three core engineering domains:
1. **Automated CI/CD Quality Gate (Jenkins):** Code linting, unit testing (Pytest), Terraform validation, and Docker validation.
2. **Cloud Infrastructure (Terraform & AWS):** Isolated Ubuntu 24.04 LTS host running PostgreSQL 17.6 and Apache Superset 6.0.0 in Docker Compose.
3. **Observability & Alerting (AWS CloudWatch):** Hypervisor metrics, CloudWatch Agent OS metrics, operational dashboard, and automated CPU alarm.

```mermaid
flowchart TD
    subgraph CI_CD["Continuous Integration (Jenkins)"]
        A["Git Repository Push"] --> B["Stage 1: Checkout"]
        B --> C["Stage 2: Environment"]
        C --> D["Stage 3: Python Validation"]
        D --> E["Stage 4: Pytest Suite (12 Tests)"]
        E --> F["Stage 5: Terraform Validate"]
        F --> G["Stage 6: Docker Config Check"]
        G --> H["Stage 7: Quality Gate Passed"]
    end

    subgraph AWS_Cloud["AWS Cloud (ap-southeast-2)"]
        subgraph EC2_Host["EC2 Instance: i-079665241b02585f8 (m7i-flex.large)"]
            SG["Security Group (Port 22 SSH only from Admin /32)"]
            
            subgraph Docker_Engine["Docker Compose Runtime"]
                PSQL["PostgreSQL 17.6\n(127.0.0.1:5432 Loopback)\nDatabases: wdi_db & superset_metadata"]
                SUPER["Apache Superset 6.0.0\n(127.0.0.1:8088 Loopback)"]
                CWA["CloudWatch Agent\n(Memory & Disk Telemetry)"]
            end
            
            EBS["Encrypted gp3 Root EBS Volume (40 GiB)\nDocker Named Volume: wdi_pgdata"]
            PSQL --> EBS
            SUPER -->|psycopg2| PSQL
        end

        subgraph Observability["Amazon CloudWatch"]
            CWD["Dashboard: WDI-ETL-Monitoring"]
            CWA_ALARM["Alarm: WDI-EC2-HighCPUUtilization\n(Threshold > 80% for 10 min)"]
            EC2_Host -.->|Hypervisor Telemetry: CPU, Network, Status| Observability
            CWA -.->|OS Telemetry: Memory, Disk| Observability
            Observability --> CWD
            Observability --> CWA_ALARM
        end
    end

    subgraph Admin_Access["Zero-Trust Administration"]
        ADMIN["Administrator Laptop"] -->|SSH Local Port Forward\nlocalhost:8088 -> EC2:8088| SG
        ADMIN -.->|AWS Console / CLI| CWD
    end
```

---

## 2. Infrastructure Specifications

| Attribute | Configuration Value | Justification |
| :--- | :--- | :--- |
| **Cloud Provider** | Amazon Web Services (AWS) | Target academic cloud provider |
| **AWS Region** | `ap-southeast-2` (Sydney) | Active infrastructure location in Terraform state |
| **EC2 Instance ID** | `i-079665241b02585f8` | Existing provisioned instance |
| **Instance Type** | `m7i-flex.large` | 2 vCPUs, 8 GiB RAM (sufficient for Polars ETL & Superset workers) |
| **Root Block Device** | 40 GiB gp3 EBS | Encrypted at rest via AWS-managed KMS key |
| **Network Security** | Loopback binding (`127.0.0.1`) | Zero public internet exposure of database or BI ports |
| **Ingress Gate** | Port 22 SSH only | Restricted strictly to `var.my_ip_cidr` (/32) |
| **Metadata Protection**| IMDSv2 Required | Protects against SSRF credential extraction |
| **Termination Safety** | `disable_api_termination = true` | Prevents accidental deletion of database host |

---

## 3. Data Flow & Warehouse Model

```text
World Bank WDI SDMX CSV (data/raw/WB_WDI.csv - 3.6 GB)
       │
       ▼
Polars LazyFrame Scan & Extraction
  • Column pruning: select 14 essential SDMX columns
  • Filter whitelist: 20 socio-economic indicators
  • Temporal filter: TIME_PERIOD <= 2023
  • Drop null observations
       │
       ▼
Transformation & Type Casting
  • Rename to snake_case warehouse schema
  • Cast year to Int32 and obs_value to Float64
       │
       ▼
Dimensional Model Loading (PostgreSQL: wdi_db)
  ├── dim_country (265 rows)
  ├── dim_indicator (20 rows)
  ├── dim_date (64 rows)
  ├── dim_sex (1 row)
  ├── dim_age (1 row)
  ├── dim_urbanisation (1 row)
  └── fact_wdi_data (212,980 rows)
       │ (Read-Only access via superset_reader)
       ▼
Apache Superset (Browser UI over SSH Tunnel)
  └── Stores UI objects, datasets, charts in superset_metadata
```

---

## 4. Monitoring & CI/CD Integration

* **Jenkins CI/CD Automation:** Formalized via root `Jenkinsfile` and `scripts/run_ci_pipeline.sh`. Executes 7 stages verifying Python bytecode syntax, running 12 unit tests, and checking Terraform and Docker Compose schemas.
* **AWS CloudWatch Observability:** Live dashboard **`WDI-ETL-Monitoring`** tracks CPU, Memory, Disk, and Network telemetry. Active alarm **`WDI-EC2-HighCPUUtilization`** evaluates CPU against an 80% threshold over 10 minutes.
