#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/aws_common.sh"
require_command aws

SERVICE="${1:-superset}"
case "$SERVICE" in
  superset|postgres) ;;
  *) echo "Usage: scripts/logs.sh [superset|postgres]" >&2; exit 2 ;;
esac

read -r STATE PUBLIC_IP < <(live_instance)
if [[ "$STATE" != "running" ]]; then
  echo "EC2 is $STATE. Start it with scripts/ec2_start.sh." >&2
  exit 1
fi
ssh_to_instance "$PUBLIC_IP"
ssh -i "$SSH_KEY_PATH" -o IdentitiesOnly=yes "ubuntu@$PUBLIC_IP" \
  "cd /opt/wdi && docker compose --env-file .env.compose logs --tail=200 -f $SERVICE"
