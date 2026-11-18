# System Architecture & Technical Design

---

## 1. High-Level Architecture Overview

The WDI ETL and Cloud Analytics platform adopts a modular, decoupled architecture consisting of three primary layers:
1. **Data Processing & Analytics Layer:** Local/Server execution of high-performance Polars extraction, relational modeling, and Apache Superset visualization.
2. **Cloud Infrastructure & Storage Layer:** AWS Sydney (`ap-southeast-2`) hosting an encrypted EC2 virtual machine, EBS persistent storage, and PostgreSQL warehouse.
3. **Continuous Integration & Observability Layer:** Jenkins LTS automating quality gates and testing via GitHub Poll SCM, coupled with Amazon CloudWatch tracking system health and resource consumption.

```mermaid
flowchart TD
    subgraph SCM["Source Control & Versioning"]
        GH[("GitHub Repository\n(KumawatCodes/wdi-etl-pipeline)")]
    end

    subgraph CI["Continuous Integration (Local Docker Engine)"]
        JK["Jenkins LTS Controller\n(wdi-jenkins:8080)"]
        PL["Pipeline Stages\n• Checkout SCM\n• Python Syntax\n• 12 Pytest Tests\n• Terraform Validate\n• Docker Validation"]
        JK -->|Executes| PL
    end

    subgraph ETL["ETL & Data Pipeline Engine"]
        RAW[("Raw WDI CSV Data\n(3.6 GB, 1960-2023)")]
        EXT["Extract Engine\n(Polars LazyFrames)"]
        TRF["Transform Engine\n(Whitelist & Type Casting)"]
        LOAD["Load Engine\n(Star Schema Batch Loader)"]
        RAW --> EXT --> TRF --> LOAD
    end

    subgraph AWS["AWS Cloud Environment (ap-southeast-2 Sydney)"]
        subgraph EC2["EC2 Instance (m7i-flex.large: i-079665241b02585f8)"]
            subgraph DockerCompose["Docker Compose Runtime"]
                PG[("PostgreSQL 17.6\n(Star Schema Warehouse)")]
                SUPERSET["Apache Superset 6.0.0\n(BI Dashboards)"]
                SUPERSET -->|Port 5432 Internal| PG
            end
            EBS[("Encrypted gp3 EBS Volume\n(40 GiB Root Storage)")]
            DockerCompose --- EBS
        end
        CW["Amazon CloudWatch\n• Dashboard: WDI-ETL-Monitoring\n• Alarm: HighCPUUtilization (>80%)"]
        EC2 -.->|Hypervisor Telemetry| CW
    end

    subgraph Operator["Operator / Administrator"]
        DEV["Developer Workstation"]
        SSH["Authenticated SSH Tunnel\n(localhost:8088 -> EC2:8088)"]
        DEV -->|git push| GH
        GH -->|Poll SCM H/3 * * * *| JK
        LOAD -->|Direct or Restored Load| PG
        DEV -->|Web Browser| SSH --> SUPERSET
    end
```

---

## 2. Application Architecture

The application tier is designed around a functional, modular Python architecture located under `etl/`, `core/`, and `run_pipeline.py`.

```mermaid
flowchart LR
    subgraph CoreModule["core/"]
        LOG["logging.py\nCustom Formatter & Log Handlers"]
    end

    subgraph ETLModules["etl/"]
        E["extract.py\n• LazyFrame Reader\n• Whitelist Filter\n• Drop Null Obs Values"]
        T["transform.py\n• Column Normalization\n• Strict Type Casting\n(Int32, Float64)"]
        L["load.py\n• Dimension Extraction\n• Surrogate Key Generation\n• Fact Mapping & Upsert"]
    end

    CLI["run_pipeline.py\n(CLI Orchestrator & Entry Point)"]

    CLI --> LOG
    CLI --> E
    E --> T
    T --> L
    L --> DB[("PostgreSQL Target Database")]
```

### 2.1 Extraction Subsystem (`etl/extract.py`)
* Leverages `polars.scan_csv()` to initiate streaming scan operations without loading the entire 3.6 GB file into memory.
* Applies predicate pushdown filtering for:
  - Year $\le 2023$.
  - 20 whitelisted indicator codes covering Demographics, GDP, Health, Education, and Energy.
  - Non-null `OBS_VALUE` filtering to eliminate sparse matrix blanks.

### 2.2 Transformation Subsystem (`etl/transform.py`)
* Standardizes column headers from SDMX format to warehouse naming conventions:
  - `REF_AREA` $\to$ `country_code`
  - `INDICATOR` $\to$ `indicator_code`
  - `TIME_PERIOD` $\to$ `year`
  - `OBS_VALUE` $\to$ `obs_value`
* Strictly casts data types using Polars expressions:
  - `year` cast from string/float $\to$ `pl.Int32`
  - `obs_value` cast to `pl.Float64`

### 2.3 Loading Subsystem (`etl/load.py`)
* Deconstructs the unified dataset into normalized dimension tables:
  1. `dim_country` (Unique `country_code`, `country_name`)
  2. `dim_indicator` (Unique `indicator_code`, `indicator_name`, `unit_measure`)
  3. `dim_date` (Unique `year`)
  4. `dim_sex` (`sex_code`, `sex_label`)
  5. `dim_age` (`age_code`, `age_label`)
  6. `dim_urbanisation` (`urban_code`, `urban_label`)
* Maps generated surrogate foreign keys back to the observation rows.
* Executes chunked database insertion into `fact_wdi_data` using SQLAlchemy and `psycopg2`.

---

## 3. Data Warehouse Dimensional Model (Star Schema)

The analytical data warehouse is structured as an **Extended Star Schema** optimized for online analytical processing (OLAP) queries:

```mermaid
erDiagram
    DIM_COUNTRY ||--o{ FACT_WDI_DATA : "has observations"
    DIM_INDICATOR ||--o{ FACT_WDI_DATA : "measures"
    DIM_DATE ||--o{ FACT_WDI_DATA : "occurred on"
    DIM_SEX ||--o{ FACT_WDI_DATA : "segmented by"
    DIM_AGE ||--o{ FACT_WDI_DATA : "categorized by"
    DIM_URBANISATION ||--o{ FACT_WDI_DATA : "stratified by"

    DIM_COUNTRY {
        int country_id PK
        varchar country_code UK
        varchar country_name
    }

    DIM_INDICATOR {
        int indicator_id PK
        varchar indicator_code UK
        varchar indicator_name
        varchar unit_measure
    }

    DIM_DATE {
        int date_id PK
        int year UK
    }

    DIM_SEX {
        int sex_id PK
        varchar sex_code UK
        varchar sex_label
    }

    DIM_AGE {
        int age_id PK
        varchar age_code UK
        varchar age_label
    }

    DIM_URBANISATION {
        int urban_id PK
        varchar urban_code UK
        varchar urban_label
    }

    FACT_WDI_DATA {
        bigint fact_id PK
        int country_id FK
        int indicator_id FK
        int date_id FK
        int sex_id FK
        int age_id FK
        int urban_id FK
        double_precision obs_value
    }
```

---

## 4. Cloud Infrastructure Architecture (AWS Sydney)

The cloud environment is hosted in **AWS Sydney (`ap-southeast-2`)** and provisioned via declarative Terraform scripts:

```mermaid
flowchart TD
    subgraph AWSCloud["AWS Cloud (ap-southeast-2 Sydney)"]
        subgraph VPC["Default VPC (172.31.0.0/16)"]
            subgraph Subnet["Public Subnet (ap-southeast-2a)"]
                subgraph SG["Security Group: wdi-superset-host"]
                    direction TB
                    INGRESS["Inbound Rules:\n• TCP Port 22 (SSH) from Operator Public IP Only\n• Port 5432 (Postgres): BLOCKED\n• Port 8088 (Superset): BLOCKED"]
                    EGRESS["Outbound Rules:\n• 0.0.0.0/0 (All traffic for packages/Docker/updates)"]
                end

                subgraph VM["EC2 Compute Instance: wdi-superset\n(i-079665241b02585f8)"]
                    TYPE["Type: m7i-flex.large (2 vCPU, 8 GiB RAM)\nOS: Ubuntu 24.04 LTS (Noble Numbat)\nMetadata: IMDSv2 Required"]
                    EBS_VOL[("Root EBS Volume:\n• 40 GiB gp3\n• AES-256 Encrypted\n• delete_on_termination: false")]
                end
                SG --- VM
                VM --- EBS_VOL
            end
        end

        subgraph CWService["Amazon CloudWatch Service"]
            DASH["Dashboard: WDI-ETL-Monitoring\n(6 Widgets: CPU, Net, Status, EBS, Markdown)"]
            ALARM["Metric Alarm: WDI-EC2-HighCPUUtilization\n(Threshold > 80% for 10 min)"]
        end
        VM -.->|Hypervisor Telemetry| CWService
    end

    ADMIN["Administrator Workstation"] -->|SSH Key: wdi-superset-admin| INGRESS
```

---

## 5. CI/CD Architecture (Jenkins LTS)

The CI/CD pipeline implements a strict automated quality gate before any code is approved for production deployment.

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer
    participant GH as GitHub (KumawatCodes/wdi-etl-pipeline)
    participant JK as Jenkins LTS (wdi-jenkins:8080)
    participant Agent as Docker Execution Agent

    Dev->>GH: git push origin master
    loop Every 3 Minutes (Poll SCM: H/3 * * * *)
        JK->>GH: git ls-remote (Query remote HEAD)
    end
    GH-->>JK: Changes detected (New commit SHA)
    JK->>Agent: Trigger Pipeline Build

    activate Agent
    Agent->>Agent: Stage 1: Checkout SCM (Clean clone & commit log)
    Agent->>Agent: Stage 2: Environment Setup (Verify Python, Pytest, Terraform, Docker)
    Agent->>Agent: Stage 3: Python Validation (Bytecode syntax compile: py_compile)
    Agent->>Agent: Stage 4: Testing Suite (12 Pytest tests -> JUnit XML)
    Agent->>Agent: Stage 5: Terraform Validation (fmt -check, init -backend=false, validate)
    Agent->>Agent: Stage 6: Docker Validation (docker compose config --quiet, Dockerfile audit)
    Agent->>Agent: Stage 7: Quality Gate & Final Summary (Status: SUCCESS)
    deactivate Agent

    JK-->>Dev: Build Succeeded (#6 verified)
```

---

## 6. Container Architecture & Service Orchestration

Docker Compose orchestrates the service runtime on the EC2 host:

| Service Name | Container Name | Image Source | Port Mapping | Internal Network | Storage Volumes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Database** | `wdi-db` | `postgres:17.6` | `127.0.0.1:5432:5432` | `wdi-internal` | `wdi_postgres_data:/var/lib/postgresql/data` |
| **Analytics BI** | `wdi-superset` | Custom build from `superset-image/Dockerfile` | `127.0.0.1:8088:8088` | `wdi-internal` | `wdi_superset_home:/app/superset_home` |
| **CI/CD** | `wdi-jenkins` | Custom build from `jenkins/Dockerfile` | `0.0.0.0:8080:8080`, `50000:50000` | Host Bridge | `wdi-jenkins-ci_jenkins_home:/var/jenkins_home` |

```mermaid
flowchart TD
    subgraph Host["EC2 Host Operating System / Docker Daemon"]
        subgraph BridgeNet["Docker Internal Network: wdi-internal (bridge)"]
            DB["wdi-db\n(PostgreSQL 17.6)"]
            BI["wdi-superset\n(Apache Superset 6.0.0)"]
            BI -->|PostgreSQL Wire Protocol| DB
        end

        subgraph Storage["Docker Named Volumes on EBS gp3"]
            VOL_DB[("wdi_postgres_data")]
            VOL_BI[("wdi_superset_home")]
        end

        DB --- VOL_DB
        BI --- VOL_BI

        subgraph LocalBinds["Host Loopback Interfaces"]
            LP_DB["127.0.0.1:5432\n(Postgres Port)"]
            LP_BI["127.0.0.1:8088\n(Superset Port)"]
        end

        DB --- LP_DB
        BI --- LP_BI
    end

    EXT_NET["Public Internet / Direct Ingress"] -.->|BLOCKED BY FIREWALL| LP_DB
    EXT_NET -.->|BLOCKED BY FIREWALL| LP_BI
    SSH_CLIENT["Authenticated SSH Tunnel\n(ssh -L 8088:localhost:8088)"] ===> LP_BI
```

---

## 7. Network Communication & Security Flow

1. **Inbound Traffic Rules:**
   - Security Group `wdi-superset-host` restricts inbound port 22 (SSH) strictly to the developer/operator's specific CIDR IP (`var.my_ip_cidr`).
   - Ports 5432 (Postgres) and 8088 (Superset) are **not exposed** in the Security Group.
   - Inside the EC2 host, container ports are bound strictly to `127.0.0.1`.
2. **Accessing Superset:**
   - The operator establishes an authenticated encrypted SSH tunnel:
     ```bash
     ssh -i keys/wdi-superset-admin -L 8088:localhost:8088 -N ubuntu@<EC2_PUBLIC_IP>
     ```
   - The user opens `http://localhost:8088` locally, securely bridging traffic through the tunnel into the container.
3. **Outbound Traffic Rules:**
   - Security Group allows outbound `0.0.0.0/0` enabling OS security updates, package retrieval, Docker image pulls, and CloudWatch metrics dispatching.
