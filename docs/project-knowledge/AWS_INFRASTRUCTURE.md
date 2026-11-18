# AWS Cloud Infrastructure Specification & State Audit

---

## 1. Cloud Context & Verified Resource Inventory

* **AWS Account ID:** `529840262552`
* **Target AWS Region:** `ap-southeast-2` (Asia Pacific - Sydney)
* **Provisioning Method:** Terraform (Declarative HCL in `terraform/`)
* **Audit Execution Mode:** Strict Read-Only (Audited live on 2026-11-17)

```text
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           AWS CLOUD RESOURCE DEPLOYMENT STATUS                          │
├──────────────────────────┬─────────────────────────────┬──────────────┬─────────────────┤
│ Resource Type            │ Identifier / Name           │ Deployment   │ Live State      │
├──────────────────────────┼─────────────────────────────┼──────────────┼─────────────────┤
│ EC2 Instance             │ i-079665241b02585f8         │ DEPLOYED     │ stopped         │
│ Security Group           │ wdi-superset-host           │ DEPLOYED     │ active          │
│ Key Pair                 │ wdi-superset-admin          │ DEPLOYED     │ active          │
│ EBS Root Storage         │ 40 GiB gp3 (Encrypted)      │ DEPLOYED     │ attached        │
│ CloudWatch Dashboard     │ WDI-ETL-Monitoring          │ DEPLOYED     │ active          │
│ CloudWatch Metric Alarm  │ WDI-EC2-HighCPUUtilization  │ DEPLOYED     │ state: OK       │
│ IAM Instance Profile     │ WDICloudWatchAgentRole      │ UNDEPLOYED   │ local file only │
│ CloudWatch Guest Agent   │ amazon-cloudwatch-agent     │ UNDEPLOYED   │ not installed   │
│ SNS Notification Topic   │ Alert Topic                 │ UNDEPLOYED   │ actions empty   │
└──────────────────────────┴─────────────────────────────┴──────────────┴─────────────────┘
```

> [!IMPORTANT]
> **Distinction Between Existing vs. Undeployed Resources:**
> * **Existing:** EC2 VM, EBS volume, Security Group, SSH Key Pair, CloudWatch Dashboard, and CloudWatch Alarm are live on AWS.
> * **Undeployed / Local Only:** The custom IAM role policy (`monitoring/cloudwatch/iam_cloudwatch_agent_policy.json`) and the agent JSON config (`monitoring/cloudwatch/amazon-cloudwatch-agent.json`) exist in the git repository as reference templates, but have **not** been applied to the AWS account or attached to the EC2 host.

---

## 2. Compute Infrastructure (Amazon EC2)

* **Instance Identifier:** `i-079665241b02585f8`
* **Name Tag:** `wdi-superset`
* **Instance Type:** `m7i-flex.large`
  * **vCPUs:** 2
  * **Memory:** 8.0 GiB
  * **Processor Architecture:** 64-bit x86_64 (Intel Xeon 4th Gen Scalable processor / Emerald Rapids)
  * **Hypervisor:** AWS Nitro System
* **Operating System / AMI:** Canonical Ubuntu 24.04 LTS (`noble`) AMI `ami-000c0f4df21e3f885`
* **Instance Metadata Service (IMDS):** **IMDSv2 Enforced** (`http_tokens = "required"`, `http_endpoint = "enabled"`). Defends against Server-Side Request Forgery (SSRF) token extraction.
* **Termination Protection:** Enabled (`disable_api_termination = true`).
* **Current Power State:** `stopped` (Maintained in stopped state outside active demos to eliminate compute charges).
* **Private IP:** `172.31.7.169`
* **Public IP:** Dynamically allocated on boot when started; `null` while stopped.

---

## 3. Storage Infrastructure (Amazon EBS & Docker Volumes)

### 3.1 Root EBS Block Device
* **Volume Type:** `gp3` (General Purpose SSD)
* **Provisioned Size:** 40 GiB
* **Encryption:** **Enabled** (`encrypted = true`) using default AWS KMS EBS managed key (`alias/aws/ebs`).
* **Lifecycle Guard:** `delete_on_termination = false` (Guarantees that database files and Docker volumes persist even if the compute instance is accidentally terminated).
* **Throughput / IOPS:** Baseline 3,000 IOPS and 125 MiB/s throughput.

### 3.2 Host Docker Storage
* **Docker Root Dir:** `/var/lib/docker` located on the encrypted EBS root partition.
* **Persistent Volumes:**
  * `wdi_postgres_data`: Persists the PostgreSQL data cluster (`/var/lib/postgresql/data`).
  * `wdi_superset_home`: Persists SQLite metadata and Superset application configs (`/app/superset_home`).

---

## 4. Network Security & Firewalls (VPC & Security Groups)

* **VPC:** Default AWS VPC (`vpc-0c2d3a...` in `ap-southeast-2`) with DNS resolution and hostnames enabled.
* **Subnet:** Public Subnet in Availability Zone `ap-southeast-2a`.
* **Security Group Name:** `wdi-superset-host`

### 4.1 Ingress Security Rules
| Type | Protocol | Port Range | Source | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **SSH** | `TCP` | `22` | `<OPERATOR_PUBLIC_IP>/32` | Administrative SSH and secure port-forwarded tunnel access. |
| **PostgreSQL**| `TCP` | `5432` | **NONE (BLOCKED)** | Database is strictly unexposed to the public internet. |
| **Superset BI**| `TCP` | `8088` | **NONE (BLOCKED)** | BI dashboard port is accessible only through authenticated SSH tunnel. |

### 4.2 Egress Security Rules
| Type | Protocol | Port Range | Destination | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **All Traffic** | `ALL` | `0 - 65535` | `0.0.0.0/0` | Enables apt updates, Docker image pulls, and CloudWatch metrics ingestion. |

---

## 5. Identity & Access Management (IAM)

* **EC2 Instance Profile:** `null` (No IAM Instance Profile is currently associated with `i-079665241b02585f8`).
* **Local Reference Policy:** Located at `monitoring/cloudwatch/iam_cloudwatch_agent_policy.json`:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "cloudwatch:PutMetricData",
          "ec2:DescribeVolumes",
          "ec2:DescribeTags",
          "logs:PutLogEvents",
          "logs:CreateLogStream",
          "logs:CreateLogGroup",
          "ssm:GetParameter"
        ],
        "Resource": "*"
      }
    ]
  }
  ```
* **Architecture Note:** Because no IAM Role with `cloudwatch:PutMetricData` is attached to the EC2 host, guest operating system metrics (`CWAgent` namespace) cannot be ingested into CloudWatch. Standard EC2 hypervisor metrics (`AWS/EC2`) operate independently of IAM roles.

---

## 6. AWS CLI Management & Operational Commands

### Check Instance Status:
```bash
aws ec2 describe-instances \
  --instance-ids i-079665241b02585f8 \
  --region ap-southeast-2 \
  --query 'Reservations[0].Instances[0].[InstanceId,State.Name,PublicIpAddress]' \
  --output table
```

### Start Instance (Demo / Presentation Session):
```bash
aws ec2 start-instances --instance-ids i-079665241b02585f8 --region ap-southeast-2
```

### Stop Instance (Cost Savings after Demo):
```bash
aws ec2 stop-instances --instance-ids i-079665241b02585f8 --region ap-southeast-2
```

### Establish Encrypted SSH Port-Forward Tunnel:
```bash
ssh -i keys/wdi-superset-admin -L 8088:localhost:8088 -N ubuntu@<PUBLIC_IP>
```
