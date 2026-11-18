# Project Operational Status & Component Audit

---

## 1. Complete Component Implementation Matrix

| Component | Implemented | Verified | Missing | Notes |
| :--- | :---: | :---: | :---: | :--- |
| **Polars Extraction Engine** | **YES** | **YES** | None | Reads 3.6GB CSV with streaming LazyFrames, filtering 20 indicators for years $\le 2023$. |
| **Transformation Subsystem** | **YES** | **YES** | None | Renames columns canonically; strictly casts year to `Int32` and obs_value to `Float64`. |
| **Star Schema Data Warehouse**| **YES** | **YES** | None | 6 Dimensions (`dim_country`, `dim_indicator`, `dim_date`, `dim_sex`, `dim_age`, `dim_urbanisation`) and `fact_wdi_data`. |
| **Automated Pytest Suite** | **YES** | **YES** | None | 12 automated unit/integration tests running under pytest and reporting to JUnit XML. |
| **Jenkins LTS Controller** | **YES** | **YES** | None | Containerized in `wdi-jenkins` on `localhost:8080` with persistent storage volume. |
| **Jenkins Declarative Pipeline**| **YES** | **YES** | None | 7-stage quality gate (`Jenkinsfile`) validating code, tests, Terraform, and Docker. |
| **GitHub SCM Poll Integration** | **YES** | **YES** | None | Poll SCM on schedule `H/3 * * * *` tracking `origin/master`. Build #6 automatically triggered. |
| **Terraform IaC Definitions** | **YES** | **YES** | None | Formatted (`fmt`), initialized, and validated (`validate`) in `terraform/main.tf`. |
| **AWS EC2 Compute Host** | **YES** | **YES** | None | `m7i-flex.large` (`i-079665241b02585f8`) in `ap-southeast-2` (currently stopped). |
| **AWS Encrypted EBS Storage** | **YES** | **YES** | None | 40 GiB gp3 encrypted volume with `delete_on_termination = false`. |
| **Apache Superset BI Server** | **YES** | **YES** | None | Containerized via custom Dockerfile running as non-root user `superset`. |
| **Secure SSH Port Tunneling** | **YES** | **YES** | None | Access routed over loopback port `8088` without public web exposure. |
| **CloudWatch Dashboard** | **YES** | **YES** | None | `WDI-ETL-Monitoring` exists with 6 widgets displaying live telemetry. |
| **CloudWatch Metric Alarm** | **YES** | **YES** | None | `WDI-EC2-HighCPUUtilization` active in state `OK` (`CPUUtilization > 80%`). |
| **CloudWatch Guest OS Agent** | **NO** | **NO** | Agent binary | `amazon-cloudwatch-agent` not installed on guest OS (documentation template only). |
| **CloudWatch Mem/Disk Metrics**| **NO** | **NO** | Ingestion | `CWAgent` namespace is empty (requires OS agent and IAM profile). |
| **IAM Instance Profile** | **NO** | **NO** | Deployment | Policy template exists in repo, but EC2 has `IamInstanceProfile: null`. |
| **Alarm Notification Actions** | **NO** | **NO** | SNS Topic | Deliberately left unconfigured (`Actions: []`) per authorization rules. |

---

## 2. Categorized Status Breakdown

### 2.1 Completed & Fully Verifiable Components
1. **ETL Processing:** Complete extraction, transformation, and dimensional loading pipeline.
2. **Database Warehousing:** Schema definitions (`schema_safe.sql`) and database persistence.
3. **Automated Testing:** 12/12 passing unit tests covering all data transformation rules.
4. **CI/CD Quality Gate:** Jenkins LTS pipeline executing 7 automated stages with JUnit test reporting.
5. **Git SCM Automation:** Automated build triggering via Jenkins SCM Polling (`H/3 * * * *`).
6. **Cloud Infrastructure as Code:** Terraform definitions for VPC, Security Group, SSH Key, and EC2 host.
7. **Cloud Hypervisor Monitoring:** CloudWatch dashboard `WDI-ETL-Monitoring` and metric alarm `WDI-EC2-HighCPUUtilization`.
8. **Container Security:** Non-root Superset execution, loopback port binding, and encrypted storage.

### 2.2 Partially Completed / Documentation-Only Components
1. **CloudWatch Guest OS Telemetry (`CWAgent`):** The configuration file (`monitoring/cloudwatch/amazon-cloudwatch-agent.json`) and IAM policy (`iam_cloudwatch_agent_policy.json`) are documented in the repository, but the agent was not installed on the live EC2 host. Hypervisor metrics (`AWS/EC2`) cover CPU, Network, Health, and EBS I/O.
2. **IAM Instance Profile:** Documented in architecture references, but unattached in AWS IAM (`IamInstanceProfile: null`).

### 2.3 Deliberately Not Implemented (Per Scope & Authorization Constraints)
1. **Automated Continuous Deployment (CD):** Deliberately omitted to prevent accidental database overwrites or schema corruption during presentations.
2. **SNS Alarm Endpoints:** Deliberately left empty (`AlarmActions: []`) to avoid generating false notifications.
3. **Public Ingress / Ngrok Tunnels:** Deliberately rejected to maintain zero-ingress security for Jenkins and Superset.
4. **Prometheus / Grafana / Kubernetes:** Omitted per university scope authorization.

---

## 3. Planned Improvements & Roadmap

1. **Automate CloudWatch Agent Bootstrap:** Add `amazon-cloudwatch-agent` installation and configuration into Terraform `user_data.sh`.
2. **Terraform IAM Module:** Provision `aws_iam_role` and `aws_iam_instance_profile` directly within `terraform/main.tf` to enable guest OS metrics automatically.
3. **Application Load Balancer (ALB):** Replace SSH port forwarding with an AWS ALB, AWS WAF, and ACM SSL certificate if public multi-user dashboard access is required.
4. **Automated Database Snapshots:** Add an AWS Backup plan or cron job to automate nightly encrypted EBS snapshots.
