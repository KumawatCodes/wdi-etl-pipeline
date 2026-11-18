# Project Overview: World Development Indicators (WDI) ETL & Cloud Analytics Platform

---

## 1. Executive Summary & Identity

* **Project Title:** World Bank Development Indicators (WDI) Automated ETL & Cloud Analytics Platform
* **Domain:** Enterprise Data Engineering, Cloud Infrastructure, DevOps / CI/CD, Business Intelligence
* **Primary Repository:** `https://github.com/KumawatCodes/wdi-etl-pipeline.git`
* **Target Environment:** Hybrid Cloud (Local Jenkins LTS CI/CD & Local Development + AWS `ap-southeast-2` Cloud Warehouse & BI)
* **Audience:** Cloud Architects, DevOps Engineers, Data Platform Engineers, and Academic Evaluators

---

## 2. Problem Statement & Motivation

The **World Bank World Development Indicators (WDI)** represents one of the premier global socio-economic datasets, capturing hundreds of development metrics across 200+ nations and regional aggregates spanning over six decades (1960–2023). 

However, raw global development data suffers from critical engineering challenges:
1. **Massive Volume & Memory Bottlenecks:** The raw CSV dataset exceeds **3.6 GB** uncompressed. Traditional data analysis tools (such as standard Pandas or spreadsheets) exhaust memory (OOM) when attempting in-memory joins and filters.
2. **Unnormalized & Redundant Schemas:** Raw records contain denormalized textual indicators, country descriptions, age breakdowns, sex classifications, and urbanization labels repeatedly across millions of rows.
3. **Query Inefficiency for Business Intelligence:** Direct querying against multi-gigabyte flat tables degrades dashboard responsiveness in tools like Apache Superset. Analytical queries require aggregations across specific indicators, regions, and time horizons.
4. **Lack of Automated Quality Assurance:** Data ingestion pipelines without strict validation risk inserting malformed records, null observation values, or schema drifts into downstream analytics warehouses.
5. **Infrastructure Drift & Cost Sprawl:** Cloud data warehouses frequently incur runaway operational costs if compute resources are left running unmonitored or provisioned without reproducible Infrastructure as Code (IaC).

---

## 3. The Solution

The **WDI ETL & Cloud Analytics Platform** resolves these challenges by combining high-performance columnar data processing, relational star-schema warehousing, Infrastructure as Code, automated CI/CD quality gates, and cloud observability:

```text
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                END-TO-END PLATFORM LIFECYCLE                            │
└─────────────────────────────────────────────────────────────────────────────────────────┘
   [Raw 3.6GB CSV] 
          │
          ▼
   [Polars LazyFrame ETL] ──(Filter, Cast, Whitelist)──► [Clean In-Memory DataFrames]
                                                                  │
                                                                  ▼
   [PostgreSQL 17.6 Warehouse] ◄──(Batch Dimension/Fact Load)─────┘
   (Star Schema: 6 Dimensions + Fact Table)
          │
          ▼
   [Apache Superset 6.0 BI] ──(SSH Tunnel / Loopback 8088)──► [Interactive Dashboards]
          ▲
          │ Provisioned & Monitored by
   [Terraform IaC] ──(AWS Sydney ap-southeast-2)──► [EC2 m7i-flex.large + gp3 Encrypted EBS]
          ▲
          │ Monitored by
   [AWS CloudWatch] ──► [WDI-ETL-Monitoring Dashboard & HighCPUUtilization Alarm]
          ▲
          │ Verified by
   [Jenkins LTS CI/CD] ◄──(Poll SCM: H/3 * * * *)──► [GitHub Remote: master branch]
   (7-Stage Quality Gate: Python, Pytest 12 Tests, Terraform Validate, Docker Config)
```

---

## 4. Key Features & Platform Capabilities

### 4.1 High-Performance Columnar ETL Pipeline
* **Framework:** Powered by **Polars** with LazyFrame execution graphs.
* **Filter Pushdown:** Applies predicate pushdowns to extract a targeted whitelist of 20 core socio-economic indicators across 5 critical themes (Demographics, Economy & Labor, Education & Literacy, Health & Mortality, Environment & Energy).
* **Null Handling:** Filters out null or non-positive observation values before warehouse staging.
* **Schema Enforcement:** Strict type casting (Year $\to$ `Int32`, Observation Value $\to$ `Float64`, codes/labels to strict string definitions).

### 4.2 Optimized Dimensional Data Warehouse (Star Schema)
* **Database Engine:** PostgreSQL 17.6 (hosted on an encrypted EBS volume).
* **Dimensional Model:**
  * `dim_country`: ISO-3 country codes and official country names.
  * `dim_indicator`: Standardized indicator codes, descriptions, and measurement units.
  * `dim_date`: Temporal dimension tracking discrete calendar years.
  * `dim_sex`: Sex classification (`_T` Total, `_M` Male, `_F` Female).
  * `dim_age`: Demographic age groupings (`_T` All ages, specific cohorts).
  * `dim_urbanisation`: Urbanization classifications (`_T` Total, `U` Urban, `R` Rural).
  * `fact_wdi_data`: Central fact table storing observation metrics with composite surrogate keys, composite uniqueness constraints, and B-tree indexing on `(country_id, indicator_id, date_id)`.

### 4.3 Containerized Analytics & Business Intelligence
* **BI Engine:** Apache Superset 6.0.0.
* **Custom Security:** Non-root execution using a custom `superset-image/Dockerfile` based on `apache/superset`.
* **Zero-Ingress Security:** Access is strictly routed over an authenticated SSH port-forwarded tunnel (`localhost:8088`), preventing public web exposure of sensitive analytical interfaces.

### 4.4 Declarative Infrastructure as Code (Terraform)
* **Cloud Provider:** Amazon Web Services (AWS), region `ap-southeast-2` (Sydney).
* **Compute Instance:** `m7i-flex.large` (2 vCPUs, 8 GiB RAM, Nitro architecture).
* **Storage:** 40 GiB encrypted EBS gp3 root storage volume with deletion protection.
* **Security Controls:** Enforced IMDSv2 (`http_tokens = "required"`), restrictive security group allowing inbound SSH only from the operator's current IP address, and complete removal of public database ports.

### 4.5 Continuous Integration & Automated Quality Gates (Jenkins LTS)
* **CI/CD Orchestrator:** Containerized Jenkins LTS (`wdi-jenkins`) running locally at `http://localhost:8080`.
* **GitHub Integration:** Configured with **Poll SCM** (`H/3 * * * *`) tracking `origin/master`. Automatically detects upstream commits and executes builds without exposing Jenkins via public webhooks, reverse proxies, or tunnels.
* **Automated Stages:**
  1. *Checkout:* Clones git repository, logs commit SHA, ensures clean working tree.
  2. *Environment:* Verifies Python runtime (Python 3.13), Pytest, Terraform, and Docker CLI.
  3. *Validation:* Performs static bytecode syntax compilation (`py_compile`) across all ETL modules.
  4. *Testing:* Executes **12 automated Pytest unit tests** covering extraction, casting, and dimensional mapping with JUnit XML report generation.
  5. *Terraform Validation:* Enforces HCL formatting (`fmt -check`), initializes provider cache, and validates syntax (`validate`).
  6. *Docker Validation:* Verifies Docker Compose schemas and Superset Dockerfile non-root security.
  7. *Final Report:* Summarizes build quality gate status.

### 4.6 Cloud Monitoring & Observability (AWS CloudWatch)
* **Dashboard:** `WDI-ETL-Monitoring` in `ap-southeast-2`.
* **Telemetry Widgets:** Real-time tracking of EC2 CPU Utilization (Average & Maximum), Network I/O (In vs Out), Hypervisor/Instance Health Status Checks, EBS Storage Throughput, and Architectural Reference Metadata.
* **Metric Alarm:** `WDI-EC2-HighCPUUtilization` configured with `CPUUtilization > 80%` over 2 consecutive 5-minute evaluation periods (`TreatMissingData: notBreaching`).

---

## 5. Major Engineering Decisions & Trade-Offs

| Decision | Selected Approach | Alternative Considered | Technical Justification |
| :--- | :--- | :--- | :--- |
| **ETL Engine** | Polars (LazyFrames) | Pandas | Polars processes the 3.6GB dataset with parallel Rust execution and query optimization, avoiding high memory overhead and out-of-memory crashes. |
| **Warehouse Schema**| Star Schema (6 Dims + Fact)| 3NF or Single Flat Table | OLAP star schema drastically simplifies aggregations, optimizes join performance for Apache Superset, and minimizes storage through foreign key integer IDs. |
| **Jenkins Hosting** | Local Docker Compose | New AWS EC2 Instance | Running Jenkins locally in Docker saves student cloud budget, avoids idle compute fees, and ensures zero public attack surface. |
| **SCM Trigger** | Poll SCM (`H/3 * * * *`) | GitHub Webhooks / Ngrok | Jenkins is run inside an internal network. Poll SCM allows automated commit-triggered builds without exposing local ports via third-party tunnels or reverse proxies. |
| **Deployment Guard**| Decoupled CI / Manual CD | Automatic `terraform apply` | Data pipelines risk production table drops or unintended state replacements if CD is fully automated without operator sign-off. Backups must be verified before schema migration. |
| **Cloud Cost Control**| Stopped Instance Lifecycle | 24/7 Running Instance | The EC2 instance is powered down when not actively executing ETL or presenting, avoiding idle hourly charges while retaining encrypted EBS data and CloudWatch telemetry. |

---

## 6. Current Implementation & Operational Status

* **ETL Engine:** Fully implemented, verified, and operational.
* **Warehouse Schema:** Initialized with safe, non-destructive bootstrap scripts (`schema_safe.sql`).
* **CI/CD Pipeline:** Fully configured in Jenkins LTS (`WDI-ETL-Pipeline`). Build #6 passed with 100% stage success and 12/12 passing tests, triggered automatically via Poll SCM.
* **AWS Cloud Infrastructure:** Defined in Terraform. The target EC2 instance `i-079665241b02585f8` is in `stopped` state in `ap-southeast-2` to prevent charges.
* **CloudWatch Monitoring:** Dashboard `WDI-ETL-Monitoring` and Alarm `WDI-EC2-HighCPUUtilization` exist and are active with real historical telemetry.
