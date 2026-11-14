#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/aws_common.sh"

require_command aws
require_command ssh
require_command scp

COMPOSE_ENV="$PROJECT_ROOT/.env.compose"
if [[ ! -r "$COMPOSE_ENV" ]]; then
  echo "Create .env.compose from .env.example and set unique secrets before deploying." >&2
  exit 1
fi
if grep -Eq 'REPLACE_WITH|^[[:space:]]*AWS_(ACCESS_KEY_ID|SECRET_ACCESS_KEY|SESSION_TOKEN)[[:space:]]*=' "$COMPOSE_ENV"; then
  echo ".env.compose contains placeholders or AWS credentials. Fix it; only application settings belong in this file." >&2
  exit 1
fi

WDI_BACKUP="${WDI_WAREHOUSE_BACKUP:-}"
META_BACKUP="${SUPERSET_METADATA_BACKUP:-}"
if [[ ! -s "$WDI_BACKUP" || ! -s "$META_BACKUP" ]]; then
  cat >&2 <<'MSG'
Safe migration requires verified custom-format archives for both databases.
Create them with scripts/backup_db.sh, copy them under backups/, then run:
  WDI_WAREHOUSE_BACKUP=backups/<wdi-archive>.dump \
  SUPERSET_METADATA_BACKUP=backups/<metadata-archive>.dump scripts/deploy.sh
The remote restore refuses to overwrite a database containing objects.
MSG
  exit 1
fi

read -r STATE PUBLIC_IP < <(live_instance)
if [[ "$STATE" != "running" ]]; then
  echo "EC2 is $STATE. Start it with scripts/ec2_start.sh before deploying." >&2
  exit 1
fi
ssh_to_instance "$PUBLIC_IP"
REMOTE="ubuntu@$PUBLIC_IP"
SCP_OPTS=(-i "$SSH_KEY_PATH" -o IdentitiesOnly=yes)

ssh -i "$SSH_KEY_PATH" -o IdentitiesOnly=yes "$REMOTE" \
  'sudo install -d -o ubuntu -g ubuntu -m 0750 /opt/wdi /opt/wdi/backups && sudo usermod -aG docker ubuntu'

# Deliberately transfer only the application environment. The repository's
# existing .env may contain AWS credentials and is never copied to EC2.
scp "${SCP_OPTS[@]}" "$PROJECT_ROOT/docker-compose.yml" "$COMPOSE_ENV" "$REMOTE:/opt/wdi/"
scp "${SCP_OPTS[@]}" -r "$PROJECT_ROOT/docker" "$PROJECT_ROOT/superset" "$PROJECT_ROOT/superset-image" "$PROJECT_ROOT/scripts" \
  "$REMOTE:/opt/wdi/"
scp "${SCP_OPTS[@]}" "$PROJECT_ROOT/sql/schema_safe.sql" "$REMOTE:/opt/wdi/schema_safe.sql"
scp "${SCP_OPTS[@]}" "$WDI_BACKUP" "$REMOTE:/opt/wdi/backups/wdi_db.dump"
scp "${SCP_OPTS[@]}" "$META_BACKUP" "$REMOTE:/opt/wdi/backups/superset_metadata.dump"

ssh -i "$SSH_KEY_PATH" -o IdentitiesOnly=yes "$REMOTE" 'bash -se' <<'REMOTE_SCRIPT'
set -euo pipefail
cd /opt/wdi
chmod 600 .env.compose
chmod 700 backups
sudo systemctl start docker
docker compose --env-file .env.compose up -d postgres

for attempt in $(seq 1 90); do
  health="$(docker inspect --format '{{.State.Health.Status}}' wdi-postgres 2>/dev/null || true)"
  [[ "$health" == "healthy" ]] && break
  sleep 5
done
if [[ "${health:-}" != "healthy" ]]; then
  docker compose --env-file .env.compose logs --tail=100 postgres
  echo "PostgreSQL did not become healthy; stopping deployment." >&2
  exit 1
fi

./scripts/restore_db.sh backups/wdi_db.dump wdi_db
./scripts/restore_db.sh backups/superset_metadata.dump superset_metadata
./scripts/provision_reader.sh
./scripts/bootstrap_superset.sh
sudo systemctl enable --now wdi-compose.service
docker compose --env-file .env.compose ps
REMOTE_SCRIPT

echo "Deployment files and verified database archives are installed."
"$SCRIPT_DIR/verify_remote.sh"
"$SCRIPT_DIR/instance_info.sh"
