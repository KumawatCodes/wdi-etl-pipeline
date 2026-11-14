#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/aws_common.sh"
require_command aws

INSTANCE_ID="$(require_instance_id)"
REGION="$(aws_region)"
read -r STATE PUBLIC_IP < <(aws --region "$REGION" ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].[State.Name,PublicIpAddress]' \
  --output text)

echo "Instance: $INSTANCE_ID ($STATE, $REGION)"
if [[ "$STATE" != "running" || -z "$PUBLIC_IP" || "$PUBLIC_IP" == "None" ]]; then
  echo "Dashboard URL after starting the SSH tunnel: http://127.0.0.1:8088"
  echo "Start the EC2 instance with: scripts/ec2_start.sh"
  exit 0
fi

echo "Current public IP: $PUBLIC_IP"
echo "Dashboard URL after starting the SSH tunnel: http://127.0.0.1:8088"
echo "SSH: ssh -i '$SSH_KEY_PATH' ubuntu@$PUBLIC_IP"
echo "Tunnel: ssh -i '$SSH_KEY_PATH' -N -L 8088:127.0.0.1:8088 ubuntu@$PUBLIC_IP"
