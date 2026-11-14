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
echo "EC2: $INSTANCE_ID ($STATE)"
if [[ "$STATE" != "running" || -z "$PUBLIC_IP" || "$PUBLIC_IP" == "None" ]]; then
  exit 0
fi

ssh_to_instance "$PUBLIC_IP"
ssh -i "$SSH_KEY_PATH" -o IdentitiesOnly=yes "ubuntu@$PUBLIC_IP" \
  'sudo systemctl --no-pager status wdi-compose.service || true; cd /opt/wdi && docker compose --env-file .env.compose ps'
