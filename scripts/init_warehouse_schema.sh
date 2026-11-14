#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
COMPOSE_ENV="$PROJECT_ROOT/.env.compose"
[[ -r "$COMPOSE_ENV" ]] || { echo "Missing .env.compose." >&2; exit 1; }

echo "Applying the idempotent schema to the configured warehouse database. This script creates missing objects and never drops existing objects."
docker compose --env-file "$COMPOSE_ENV" exec -T postgres \
  sh -ec 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < "$PROJECT_ROOT/sql/schema_safe.sql"
