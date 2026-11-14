#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/aws_common.sh"
require_command aws
require_command ssh
require_command curl

read -r STATE PUBLIC_IP < <(live_instance)
if [[ "$STATE" != "running" ]]; then
  echo "EC2 is $STATE; start it before verifying the services." >&2
  exit 1
fi
ssh_to_instance "$PUBLIC_IP"

ssh -i "$SSH_KEY_PATH" -o IdentitiesOnly=yes "ubuntu@$PUBLIC_IP" 'bash -se' <<'REMOTE_SCRIPT'
set -euo pipefail
cd /opt/wdi

docker compose --env-file .env.compose ps
docker compose --env-file .env.compose exec -T superset \
  python -c "import urllib.request; print('Superset health:', urllib.request.urlopen('http://127.0.0.1:8088/health', timeout=10).status)"
docker compose --env-file .env.compose exec -T postgres \
  sh -ec 'PGPASSWORD="$SUPERSET_READER_PASSWORD" psql -Xv ON_ERROR_STOP=1 -h 127.0.0.1 -U superset_reader -d wdi_db -c "SELECT current_database(), current_user, (SELECT count(*) FROM fact_wdi_data) AS fact_rows"'
REMOTE_SCRIPT

# Verify the same localhost HTTP route the browser uses, through a temporary
# SSH forward. The security group still exposes SSH only.
LOCAL_PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
ssh -i "$SSH_KEY_PATH" -o IdentitiesOnly=yes -o ExitOnForwardFailure=yes \
  -N -L "127.0.0.1:$LOCAL_PORT:127.0.0.1:8088" "ubuntu@$PUBLIC_IP" \
  >/dev/null 2>&1 &
TUNNEL_PID=$!
trap 'kill "$TUNNEL_PID" 2>/dev/null || true' EXIT
curl --fail --silent --show-error --retry 20 --retry-connrefused --retry-delay 1 \
  "http://127.0.0.1:$LOCAL_PORT/health"
echo "Superset HTTP health verified through the SSH tunnel."
