# Eraser AI Architecture Prompt

> **Instructions for Use:**  
> Copy the complete prompt block below and paste it directly into **Eraser.io** (via **Create with AI** or the `/diagram` command).  
> It is strictly constructed from the verified implementation of the **WDI ETL & Cloud Analytics Platform**.

---

```text
Create a presentation-ready, professional cloud data engineering and DevOps architecture diagram in a wide landscape layout titled "End-to-End Cloud Data Engineering and DevOps Architecture".

The diagram must represent an actual implemented hybrid cloud platform for the World Bank Development Indicators (WDI) analytics system. Organize the architecture in a clean Left-to-Right orientation with visually distinct logical layers, clear container and AWS boundaries, labeled directional arrows, and standard technology icons.

### 1. LAYOUT & VISUAL STRUCTURE (LEFT-TO-RIGHT)
Arrange the components across the canvas following this logical left-to-right progression:
[Data Ingestion & SCM] --> [Processing & CI/CD Gates] --> [AWS Cloud Infrastructure & Docker Containers] --> [Analytics Visualization & CloudWatch Observability]

---

### 2. LOGICAL LAYERS & COMPONENT SPECIFICATIONS

#### GROUP A: DATA SOURCE & ETL PROCESSING (Lower-Left / Data Pipeline)
1. "Raw WDI Dataset" [Icon: document / file / database]
   - Description: "3.6 GB Uncompressed CSV (1960–2023)"
   - Details: "World Bank Development Indicators with SDMX multi-dimensional headers"
2. "Extraction Engine" [Icon: python / code]
   - Technology: "Polars LazyFrames"
   - Responsibility: "Memory-efficient streaming scan (scan_csv), predicate pushdown filtering (year <= 2023, non-null OBS_VALUE)"
3. "Transformation Subsystem" [Icon: cogs / process]
   - Technology: "Polars Vectorized Core"
   - Responsibility: "20-indicator whitelist filtering, schema normalization, strict casting to Int32 (year) and Float64 (obs_value)"
4. "Warehouse Dimensional Loader" [Icon: upload / database]
   - Technology: "SQLAlchemy & psycopg2-binary"
   - Responsibility: "Surrogate key generation, relational mapping, batch chunk loading into PostgreSQL"

---

#### GROUP B: DEVELOPER & SOURCE CONTROL LAYER (Upper-Left / DevOps Pipeline)
1. "Developer Workstation" [Icon: laptop / user]
   - Responsibility: "Local development, Pytest test execution, manual deployment trigger (scripts/deploy.sh)"
2. "GitHub Remote Repository" [Icon: github]
   - Repository: "KumawatCodes/wdi-etl-pipeline"
   - Branch: "origin/master"
   - Details: "Central Git version control tracking code, Dockerfiles, and Terraform IaC"

---

#### GROUP C: CI/CD AUTOMATION & QUALITY GATE LAYER (Center-Left / Jenkins)
1. Boundary Box: "Jenkins CI/CD Automation (Local Docker Host)" [Icon: jenkins]
   - Host: "wdi-jenkins container on localhost:8080"
   - Trigger: "Poll SCM cron schedule: H/3 * * * * (queries git ls-remote every ~3 minutes; no public webhooks or tunnels)"
   - Sequential 7-Stage Pipeline Box [Icon: list-checks / pipeline]:
     * "Stage 1: Checkout" (clean Git clone & commit SHA audit)
     * "Stage 2: Environment" (verifies Python 3.13, Pytest 9.2, Terraform v1.17, Docker CLI)
     * "Stage 3: Validation" (static py_compile bytecode syntax check across run_pipeline, etl, core)
     * "Stage 4: Automated Testing" (executes 12 Pytest unit tests, publishes JUnit XML reports)
     * "Stage 5: Terraform Validation" (terraform fmt -check, init -backend=false, validate)
     * "Stage 6: Docker Validation" (docker compose config check, superset-image Dockerfile non-root audit)
     * "Stage 7: Final Quality Gate" (aggregated status: BUILD SUCCESS)
   - Architectural Constraint: Jenkins enforces continuous integration and testing only. Continuous Deployment is decoupled and operator-managed to protect live data.

---

#### GROUP D: AWS CLOUD INFRASTRUCTURE LAYER (Center-Right / Production Host)
Surround this entire infrastructure inside a large cloud boundary labeled "AWS Cloud (Region: ap-southeast-2 Sydney)" [Icon: aws]:

1. Network Boundary: "Default VPC (172.31.0.0/16)" [Icon: aws-vpc]
   - Security Boundary: "Security Group: wdi-superset-host" [Icon: shield / firewall]
     * Inbound: "TCP Port 22 (SSH) restricted to Operator IP"
     * Inbound: "Ports 5432 (Postgres) & 8088 (Superset) completely BLOCKED from the internet"
     * Outbound: "0.0.0.0/0 (Egress for OS patches & CloudWatch telemetry)"

2. Virtual Compute Host: "EC2 Instance: wdi-superset (i-079665241b02585f8)" [Icon: aws-ec2]
   - Hardware: "m7i-flex.large (2 vCPU, 8.0 GiB RAM, Nitro System)"
   - Operating System: "Ubuntu 24.04 LTS (Noble Numbat)"
   - Security: "IMDSv2 Enforced (http_tokens = required)"
   - Lifecycle: "Controlled on-demand lifecycle (kept in stopped state outside demos to prevent idle charges)"

3. Storage: "Encrypted Root Storage (40 GiB gp3 EBS)" [Icon: aws-ebs]
   - Details: "AES-256 KMS encrypted, baseline 3000 IOPS, delete_on_termination = false"
   - Mounts: "Houses Docker named volumes (wdi_postgres_data and wdi_superset_home)"

4. Internal Container Network: "Docker Compose Runtime (wdi-internal bridge)" [Icon: docker]:
   - Container 1: "wdi-db" [Icon: postgresql]
     * Image: "postgres:17.6"
     * Local Binding: "127.0.0.1:5432 (host loopback only)"
     * Storage: "wdi_postgres_data volume"
     * Healthcheck: "pg_isready -U wdi_admin -d wdi_db"
     * Schema: "Star Schema (dim_country, dim_indicator, dim_date, dim_sex, dim_age, dim_urbanisation -> fact_wdi_data)"
   - Container 2: "wdi-superset" [Icon: apache-superset / chart]
     * Image: "Custom image based on apache/superset:6.0.0"
     * Security: "Enforced non-root user 'superset' (UID 1000)"
     * Local Binding: "127.0.0.1:8088 (host loopback only)"
     * Storage: "wdi_superset_home volume"
     * Dependency: "depends_on: wdi-db (service_healthy)"

---

#### GROUP E: SECURE USER ACCESS & BI ANALYTICS (Upper-Right)
1. "Operator / Analyst Browser" [Icon: browser / user]
2. "Authenticated SSH Tunnel" [Icon: lock / key]
   - Details: "ssh -i keys/wdi-superset-admin -L 8088:localhost:8088 -N ubuntu@<EC2_IP>"
   - Protocol: "Encrypted SSH Port Forwarding (Port 22 -> Loopback 8088)"
3. "Interactive Superset Dashboards" [Icon: dashboard / bar-chart]
   - Features: "Temporal trends, demographic comparisons, and multi-indicator analytical slices"

---

#### GROUP F: CLOUD MONITORING & OBSERVABILITY LAYER (Far-Right / CloudWatch)
Boundary Box: "Amazon CloudWatch Observability" [Icon: aws-cloudwatch]
1. "Telemetry Ingestion" [Icon: activity / line-chart]
   - Source: "AWS Nitro Hypervisor (Zero-agent hypervisor metrics)"
   - Metrics: "CPUUtilization, NetworkIn, NetworkOut, StatusCheckFailed, EBSReadBytes, EBSWriteBytes"
2. "Dashboard: WDI-ETL-Monitoring" [Icon: dashboard]
   - Widgets: "6 visual widgets displaying real 5-minute telemetry and architecture markdown"
3. "Metric Alarm: WDI-EC2-HighCPUUtilization" [Icon: bell / alert]
   - Parameters: "CPUUtilization > 80% for 2 consecutive 300s evaluation periods (10 min)"
   - Missing Data Policy: "TreatMissingData = notBreaching (prevents false alerts while stopped)"
   - Status: "State: OK"
4. Visual Limitation Note (Subdued / Dashed Box):
   - "Uninstalled Guest OS Agent (CWAgent): Memory/Disk % metrics & SNS actions not configured"

---

### 3. DIRECTIONAL CONNECTORS & LABELS

#### Data Pipeline Flow:
- "Raw WDI Dataset" --> "Extraction Engine": "Stream CSV scan (3.6 GB)"
- "Extraction Engine" --> "Transformation Subsystem": "Filtered LazyFrames"
- "Transformation Subsystem" --> "Warehouse Dimensional Loader": "Clean Batches & Whitelist"
- "Warehouse Dimensional Loader" --> "wdi-db": "SQL Insert (Star Schema)"

#### DevOps & CI/CD Flow:
- "Developer Workstation" --> "GitHub Remote Repository": "git push origin master"
- "Jenkins CI/CD Automation" --> "GitHub Remote Repository": "Poll SCM (H/3 * * * *) query"
- "GitHub Remote Repository" --> "Jenkins CI/CD Automation": "Fetch commits upon detection"
- "Jenkins CI/CD Automation" --> "Sequential 7-Stage Pipeline Box": "Execute automated quality gate"

#### Deployment & Access Flow:
- "Developer Workstation" --> "EC2 Instance: wdi-superset": "Operator Deploy (scripts/deploy.sh over SSH)"
- "Operator / Analyst Browser" --> "Authenticated SSH Tunnel": "HTTP http://localhost:8088"
- "Authenticated SSH Tunnel" --> "wdi-superset": "Secure port forward to container"
- "wdi-superset" --> "wdi-db": "Internal SQL queries (wdi-internal network)"

#### Monitoring Flow:
- "EC2 Instance: wdi-superset" --> "Telemetry Ingestion": "Hypervisor Telemetry (Nitro)"
- "Telemetry Ingestion" --> "Dashboard: WDI-ETL-Monitoring": "Populate real metric widgets"
- "Telemetry Ingestion" --> "Metric Alarm: WDI-EC2-HighCPUUtilization": "Evaluate CPU > 80%"

---

### 4. VISUAL STYLING & ACCURACY RULES
- **Orientation:** Wide landscape format, left-to-right flow.
- **Color Palette:** Restrained, professional enterprise palette (Blue for AWS/Cloud, Slate for CI/CD, Green for Data Processing, Amber for Alarms).
- **Icons:** Use official technology icons where possible (AWS, EC2, EBS, CloudWatch, Docker, Jenkins, PostgreSQL, Python, Apache Superset, GitHub).
- **Component Text:** Concise labels and bullet points; no dense paragraphs.
- **Strict Realism:** Do NOT include unverified or unused services (do NOT draw S3, RDS, Lambda, Kubernetes, Kafka, Nginx, or SNS notifications).
- **Boundary Precision:** Clearly nest `wdi-db` and `wdi-superset` containers inside the `Docker Compose Runtime` on the `EC2 Instance` within the `AWS Cloud ap-southeast-2` boundary.
```
