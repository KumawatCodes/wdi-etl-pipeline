#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/aws_common.sh"
require_command aws

INSTANCE_ID="$(require_instance_id)"
REGION="$(aws_region)"
STATE="$(aws --region "$REGION" ec2 describe-instances --instance-ids "$INSTANCE_ID" --query 'Reservations[0].Instances[0].State.Name' --output text)"
if [[ "$STATE" == "stopped" ]]; then
  echo "EC2 is already stopped. EBS storage remains attached and billed."
  exit 0
fi
aws --region "$REGION" ec2 stop-instances --instance-ids "$INSTANCE_ID" >/dev/null
aws --region "$REGION" ec2 wait instance-stopped --instance-ids "$INSTANCE_ID"
echo "EC2 stopped. Persistent EBS storage remains attached and may continue to incur charges."
