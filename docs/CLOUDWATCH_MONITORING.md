# AWS CloudWatch Monitoring & Observability Architecture

## 1. Overview & Monitoring Strategy

The WDI ETL pipeline and Apache Superset BI platform are hosted on an Amazon Web Services (AWS) EC2 virtual machine. To ensure system availability, performance stability, and operational visibility, the system integrates with **Amazon CloudWatch** for metrics collection, real-time dashboards, and automated threshold alerts.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ AWS CLOUD OBSERVABILITY (ap-southeast-2)                                    │
│                                                                             │
│  ┌──────────────────────────────┐        ┌──────────────────────────────┐  │
│  │ EC2 Hypervisor Metrics       │        │ CloudWatch Agent (OS-Level)  │  │
│  │ • CPUUtilization             │        │ • mem_used_percent           │  │
│  │ • NetworkIn / NetworkOut     │        │ • disk_used_percent          │  │
│  │ • StatusCheckFailed (Inst/Sys│        │ • tcp_established            │  │
│  │ • EBSReadBytes / WriteBytes  │        │ • swap_used_percent          │  │
│  └──────────────┬───────────────┘        └──────────────┬───────────────┘  │
│                 │                                       │                  │
│                 ▼                                       ▼                  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ Amazon CloudWatch Telemetry Engine                                   │  │
│  └──────────────────┬───────────────────────────────┬───────────────────┘  │
│                     │                               │                      │
│                     ▼                               ▼                      │
│  ┌──────────────────────────────────────┐  ┌────────────────────────────┐  │
│  │ CloudWatch Dashboard                 │  │ CloudWatch Metric Alarm    │  │
│  │ Name: WDI-ETL-Monitoring             │  │ Name:                      │  │
│  │ 6 Visual Metric & Health Widgets     │  │ WDI-EC2-HighCPUUtilization │  │
│  │ Status: ACTIVE                       │  │ Threshold: > 80% (10 min)  │  │
│  └──────────────────────────────────────┘  └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Monitored Infrastructure Context

* **AWS Region:** `ap-southeast-2` (Sydney)
* **EC2 Instance ID:** `i-079665241b02585f8`
* **Instance Type:** `m7i-flex.large` (2 vCPU, 8 GiB RAM)
* **Storage:** 40 GiB Encrypted gp3 Root EBS Volume
* **Monitored Services:** PostgreSQL 17.6 and Apache Superset 6.0.0

---

## 3. Metrics Architecture

### 3.1 Standard EC2 Hypervisor Metrics (Namespace: `AWS/EC2`)
These metrics are automatically gathered by the AWS Xen/Nitro hypervisor without guest OS agents:
* **`CPUUtilization`:** Percentage of allocated compute units currently in use.
* **`NetworkIn` & `NetworkOut`:** Total bytes received and sent across network interfaces.
* **`StatusCheckFailed`:** Composite status check; includes hardware/power (`StatusCheckFailed_System`) and operating system reachability (`StatusCheckFailed_Instance`).
* **`EBSReadBytes` & `EBSWriteBytes`:** Disk throughput between the EC2 compute instance and the EBS storage volume.

### 3.2 CloudWatch Agent Guest Metrics (Namespace: `CWAgent`)
Hypervisors cannot view guest memory or internal filesystems. The CloudWatch Agent configuration (`monitoring/cloudwatch/amazon-cloudwatch-agent.json`) collects:
* **`mem_used_percent`:** Real-time RAM utilization percentage.
* **`disk_used_percent`:** Percentage of storage used on the root partition (`/`).
* **`inodes_free`:** Available filesystem index nodes to guard against inode exhaustion during high-volume ETL logging.
* **`tcp_established`:** Active TCP network connections to identify connection leaks.

---

## 4. Least-Privilege IAM Configuration

In accordance with DevSecOps best practices, no long-term credentials or AWS Access Keys are stored on the EC2 host. The instance uses an IAM Instance Profile:

* **Role Name:** `WDICloudWatchAgentServerRole`
* **Managed Policy Attachment:** `arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy`
* **Custom Policy Definition:** `monitoring/cloudwatch/iam_cloudwatch_agent_policy.json` granting `cloudwatch:PutMetricData`, `ec2:DescribeVolumes`, `logs:PutLogEvents`, and `ssm:GetParameter`.

---

## 5. CloudWatch Dashboard: `WDI-ETL-Monitoring`

A centralized operations dashboard has been provisioned via the AWS CLI:
* **Dashboard Name:** `WDI-ETL-Monitoring`
* **Dashboard ARN:** `arn:aws:cloudwatch::529840262552:dashboard/WDI-ETL-Monitoring`
* **Region:** `ap-southeast-2`

### Dashboard Widgets Layout:
1. **Host CPU Utilization (%) [Line Graph]:** Tracks 5-minute average and maximum CPU utilization against an 80% threshold line.
2. **Network Traffic [Line Graph]:** Compares `NetworkIn` and `NetworkOut` bytes over time.
3. **Health & Status Checks [Line Graph]:** Monitors `StatusCheckFailed`, `StatusCheckFailed_Instance`, and `StatusCheckFailed_System` (0 = Healthy, 1 = Degradation).
4. **CloudWatch Agent: Memory & Disk [Line Graph]:** Real-time percentage tracking for RAM and root disk consumption.
5. **EBS Storage I/O [Line Graph]:** Throughput tracking for data persistence during ETL loads.
6. **Architecture & Project Context [Markdown Card]:** Displays critical host parameters, database identifiers, and operational guidelines.

---

## 6. CloudWatch Metric Alarm: `WDI-EC2-HighCPUUtilization`

An automated threshold alarm protects against system lockup or runaway processing:

* **Alarm Name:** `WDI-EC2-HighCPUUtilization`
* **Alarm ARN:** `arn:aws:cloudwatch:ap-southeast-2:529840262552:alarm:WDI-EC2-HighCPUUtilization`
* **Monitored Metric:** `CPUUtilization` (Namespace: `AWS/EC2`, Instance: `i-079665241b02585f8`)
* **Statistic:** Average
* **Period:** 300 seconds (5 minutes)
* **Evaluation Periods:** 2 (triggers only if CPU exceeds 80% for 10 consecutive minutes)
* **Threshold:** $\ge 80.0\%$
* **Comparison Operator:** `GreaterThanThreshold`
* **Missing Data Policy:** `notBreaching` (prevents false alarms when instance is stopped to save costs)

---

## 7. AWS Console Access Guide

To view the dashboard and alarm during a live presentation or viva defense:

1. Sign in to the **AWS Management Console**.
2. Set the active AWS Region in the top-right navbar to **Sydney (`ap-southeast-2`)**.
3. Open the **CloudWatch** service console.
4. In the left navigation menu, click **Dashboards** and select **`WDI-ETL-Monitoring`**.
5. In the left navigation menu, click **Alarms > In alarm / All alarms** and view **`WDI-EC2-HighCPUUtilization`**.

---

## 8. Command-Line Verification

Verify live metrics and resources directly via AWS CLI:

```bash
# 1. Verify CloudWatch Dashboard status
aws cloudwatch get-dashboard \
  --dashboard-name WDI-ETL-Monitoring \
  --region ap-southeast-2 \
  --query '[DashboardName,DashboardArn]' --output table

# 2. Verify CloudWatch Alarm status
aws cloudwatch describe-alarms \
  --alarm-names WDI-EC2-HighCPUUtilization \
  --region ap-southeast-2 \
  --query 'MetricAlarms[0].[AlarmName,StateValue,Threshold,Period]' --output table

# 3. Retrieve actual CPU metric datapoints
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-079665241b02585f8 \
  --start-time $(date -u -d '12 hours ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics Average Maximum \
  --region ap-southeast-2 \
  --output table
```
