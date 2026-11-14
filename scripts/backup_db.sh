#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

COMPOSE_ENV="$PROJECT_ROOT/.env.compose"
if [[ ! -r "$COMPOSE_ENV" ]]; then
  echo "Missing .env.compose. Copy .env.example and set its values first." >&2
  exit 1
fi
command -v docker >/dev/null 2>&1 || { echo "docker is required." >&2; exit 1; }

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$PROJECT_ROOT/backups"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

for DB in wdi_db superset_metadata; do
  OUT="$BACKUP_DIR/${DB}-${STAMP}.dump"
  echo "Backing up $DB to $OUT"
  docker compose --env-file "$COMPOSE_ENV" exec -T postgres \
    sh -ec 'pg_dump --format=custom --no-owner --no-privileges -U "$POSTGRES_USER" -d "$1"' sh "$DB" > "$OUT"
  docker compose --env-file "$COMPOSE_ENV" exec -T postgres \
    pg_restore --list < "$OUT" >/dev/null
  sha256sum "$OUT"
done

echo "Source WDI row count (compare with the remote verification output after restore):"
docker compose --env-file "$COMPOSE_ENV" exec -T postgres \
  sh -ec 'psql -Xv ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d wdi_db' <<'SQL'
SELECT 'fact_wdi_data=' || count(*) FROM fact_wdi_data;
SQL

echo "Both PostgreSQL archives passed pg_restore archive-list validation. Keep a copy outside this EC2 host before any infrastructure change."
