#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

COMPOSE_ENV="$PROJECT_ROOT/.env.compose"
if [[ ! -r "$COMPOSE_ENV" ]]; then
  echo "Missing .env.compose." >&2
  exit 1
fi
if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: scripts/restore_db.sh backups/<custom-format.dump> [wdi_db|superset_metadata]" >&2
  exit 2
fi

ARCHIVE="$(realpath "$1")"
case "$ARCHIVE" in
  "$PROJECT_ROOT"/backups/*) ;;
  *) echo "Place the archive under $PROJECT_ROOT/backups so Docker can read it." >&2; exit 1 ;;
esac
TARGET_DB="${2:-wdi_db}"
case "$TARGET_DB" in
  wdi_db|superset_metadata) ;;
  *) echo "Refusing to restore into unexpected database: $TARGET_DB" >&2; exit 2 ;;
esac

ARCHIVE_NAME="$(basename "$ARCHIVE")"
docker compose --env-file "$COMPOSE_ENV" exec -T postgres \
  pg_restore --list "/backups/$ARCHIVE_NAME" >/dev/null

HAS_OBJECTS="$(docker compose --env-file "$COMPOSE_ENV" exec -T postgres \
  sh -ec 'psql -XAt -U "$POSTGRES_USER" -d "$1" -c "$2"' sh "$TARGET_DB" \
  "SELECT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname NOT IN ('pg_catalog', 'information_schema') AND c.relkind IN ('r', 'p', 'S', 'v', 'm', 'f'))" | tr -d '\r')"
if [[ "$HAS_OBJECTS" != "f" ]]; then
  echo "Refusing restore: $TARGET_DB is not empty. No objects or rows were removed." >&2
  exit 1
fi

echo "Restoring $ARCHIVE into empty database $TARGET_DB. Existing objects are never dropped."
docker compose --env-file "$COMPOSE_ENV" exec -T postgres \
  sh -ec 'pg_restore --no-owner --no-privileges -U "$POSTGRES_USER" -d "$1" "/backups/$2"' sh "$TARGET_DB" "$ARCHIVE_NAME"
echo "Restore completed. Validate row counts and key queries before relying on this database."
