# AWS CloudWatch Monitoring & Observability Specification

---

## 1. Monitoring Architecture & Strategy

Cloud observability for the WDI ETL and Superset platform is implemented using **Amazon CloudWatch** in AWS Sydney (`ap-southeast-2`). The monitoring architecture distinguishes between two fundamental layers of telemetry:
1. **Hypervisor-Level Metrics (`AWS/EC2` Namespace):** Collected transparently by the AWS Nitro hypervisor outside the virtual machine. These metrics operate with zero agent footprint and require no IAM permissions.
2. **Guest Operating System Metrics (`CWAgent` Namespace):** Internal memory, disk partition, and process metrics that require the `amazon-cloudwatch-agent` package running inside the guest OS with an attached IAM Instance Profile.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AWS CLOUDWATCH OBSERVABILITY                       │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ Hypervisor Level (AWS/EC2)           │ Guest OS Level (CWAgent)             │
│ • CPUUtilization (Avg & Max)         │ • mem_used_percent                   │
│ • NetworkIn & NetworkOut             │ • disk_used_percent                  │
│ • StatusCheckFailed (Any/Sys/Inst)   │ • inodes_free                        │
│ • EBSReadBytes & EBSWriteBytes       │ • tcp_established                    │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ Status: ACTIVE (Real Telemetry)      │ Status: UNDEPLOYED (No Agent / IAM)  │
└──────────────────┬───────────────────┴──────────────────┬───────────────────┘
                   │                                      │
                   ▼                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CloudWatch Telemetry & Alarm Engine                     │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ Dashboard: WDI-ETL-Monitoring        │ Metric Alarm:                        │
│ • 6 Metric & Documentation Widgets   │ WDI-EC2-HighCPUUtilization           │
│ • Live in ap-southeast-2             │ Threshold: > 80% for 10 min          │
│ • Status: ACTIVE                     │ State: OK (TreatMissingData: NonBr)  │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

---

## 2. Latest Verified Audit Findings (As of 2026-11-17)

A strict read-only audit of AWS region `ap-southeast-2` confirmed the following verified operational state:

* **Target AWS Region:** `ap-southeast-2` (Sydney)
* **Monitored EC2 Instance:** `i-079665241b02585f8` (`m7i-flex.large`)
* **EC2 Power State at Audit:** `stopped` (Preserves cloud budget while retaining historical CloudWatch metrics).
* **Dashboard `WDI-ETL-Monitoring`:** **EXISTS** (ARN: `arn:aws:cloudwatch::529840262552:dashboard/WDI-ETL-Monitoring`).
* **CloudWatch Agent:** **NOT INSTALLED** on the EC2 host.
* **IAM Instance Profile:** `null` (No IAM role is attached to the EC2 instance).
* **Memory & Disk Metrics:** **MISSING** (Querying `CWAgent` returns `{ "Metrics": [] }`).
* **Alarm `WDI-EC2-HighCPUUtilization`:** **ACTIVE** in state **`OK`**.
* **Alarm Actions (SNS):** **NONE CONFIGURED** (`AlarmActions: []`, `OKActions: []`).

---

## 3. CloudWatch Dashboard Details (`WDI-ETL-Monitoring`)

The dashboard organizes 6 visualization widgets:

| Widget Title | Type | Namespace & Metrics | Period & Stat | Live Data Status |
| :--- | :---: | :--- | :---: | :--- |
| **EC2 Host CPU Utilization (%)** | Metric | `AWS/EC2:CPUUtilization` | 300s (Avg, Max) | **REAL DATA PRESENT** (Avg 0.76%–4.15%, Max 18.31%) |
| **Network Traffic (In vs Out)** | Metric | `AWS/EC2:NetworkIn`, `NetworkOut` | 300s (Sum) | **REAL DATA PRESENT** (2,070 B to 3,510 B) |
| **EC2 Health & Status Checks** | Metric | `AWS/EC2:StatusCheckFailed` | 300s (Max) | **REAL DATA PRESENT** (Value: 0.0, 100% healthy) |
| **CloudWatch Agent: Mem & Disk** | Metric | `CWAgent:mem_used_percent`, `disk_used_percent` | 300s (Avg) | **EMPTY** ("No data available" - agent uninstalled) |
| **EBS Storage I/O Throughput** | Metric | `AWS/EC2:EBSReadBytes`, `EBSWriteBytes` | 300s (Sum) | **REAL DATA PRESENT** (8.66 MB read burst on boot) |
| **Architecture & Reference** | Text | Markdown description | N/A | **DISPLAYING CORRECTLY** |

---

## 4. Metric Alarm Specification (`WDI-EC2-HighCPUUtilization`)

* **Alarm Name:** `WDI-EC2-HighCPUUtilization`
* **Alarm ARN:** `arn:aws:cloudwatch:ap-southeast-2:529840262552:alarm:WDI-EC2-HighCPUUtilization`
* **Monitored Metric:** `CPUUtilization` in namespace `AWS/EC2`
* **Target Dimension:** `InstanceId = i-079665241b02585f8`
* **Statistic:** `Average`
* **Period:** `300` seconds (5 minutes)
* **Evaluation Periods:** `2` (Requires 10 consecutive minutes of sustained high load to trigger)
* **Threshold:** `80.0%`
* **Comparison Operator:** `GreaterThanThreshold` (`CPUUtilization > 80%`)
* **Missing Data Policy:** `notBreaching` (Treats missing data as non-breaching; prevents false alarms when the EC2 instance is powered down).
* **Current State:** **`OK`**
* **Alarm Actions:** `[]` (**EMPTY** - No SNS topic or email endpoint attached, avoiding unauthorized notification noise).

---

## 5. Hypervisor vs. Guest OS Telemetry: Technical Comparison

| Dimension | Hypervisor Metrics (`AWS/EC2`) | Guest OS Metrics (`CWAgent`) |
| :--- | :--- | :--- |
| **Telemetry Source** | AWS Nitro Hypervisor | `amazon-cloudwatch-agent` process |
| **Installation Required** | None (Default AWS capability) | Yes (`apt install amazon-cloudwatch-agent`) |
| **IAM Permissions** | None (Hypervisor publishes directly) | Required (`cloudwatch:PutMetricData` via Instance Profile) |
| **Metrics Captured** | CPU %, Network In/Out, EBS I/O, Hardware Health | RAM %, Disk % by mount, Inodes free, TCP sockets |
| **Current Project State**| **FULLY WORKING** | **REFERENCE TEMPLATE ONLY** |

---

## 6. AWS Console Locations & CLI Commands

### Direct Console URLs:
* **Dashboard:** [WDI-ETL-Monitoring Dashboard](https://ap-southeast-2.console.aws.amazon.com/cloudwatch/home?region=ap-southeast-2#dashboards:name=WDI-ETL-Monitoring)
* **Alarm:** [WDI-EC2-HighCPUUtilization Alarm](https://ap-southeast-2.console.aws.amazon.com/cloudwatch/home?region=ap-southeast-2#alarmsV2:alarm/WDI-EC2-HighCPUUtilization)
* **EC2 Monitoring:** [i-079665241b02585f8 Monitoring Tab](https://ap-southeast-2.console.aws.amazon.com/ec2/home?region=ap-southeast-2#InstanceDetails:instanceId=i-079665241b02585f8)

### Read-Only Verification Commands:
```bash
# 1. Verify CloudWatch Dashboard
aws cloudwatch get-dashboard --dashboard-name WDI-ETL-Monitoring --region ap-southeast-2

# 2. Verify CloudWatch Alarm Status
aws cloudwatch describe-alarms --alarm-names WDI-EC2-HighCPUUtilization --region ap-southeast-2

# 3. Retrieve Historical CPU Data Points
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-079665241b02585f8 \
  --start-time 2026-11-16T00:00:00Z \
  --end-time 2026-11-17T23:59:59Z \
  --period 300 \
  --statistics Average Maximum \
  --region ap-southeast-2

# 4. Check for CWAgent Metrics
aws cloudwatch list-metrics --namespace CWAgent --region ap-southeast-2
```
