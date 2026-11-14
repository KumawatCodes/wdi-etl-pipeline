#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
COMPOSE_ENV="$PROJECT_ROOT/.env.compose"
[[ -r "$COMPOSE_ENV" ]] || { echo "Missing .env.compose." >&2; exit 1; }
cd "$PROJECT_ROOT"

docker compose --env-file "$COMPOSE_ENV" exec -T postgres \
  sh -ec 'psql -Xv ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres' <<'SQL'
\getenv reader_password SUPERSET_READER_PASSWORD
\getenv warehouse_owner POSTGRES_USER
SELECT format('CREATE ROLE superset_reader LOGIN PASSWORD %L', :'reader_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'superset_reader')
\gexec
ALTER ROLE superset_reader WITH LOGIN PASSWORD :'reader_password';
GRANT CONNECT ON DATABASE wdi_db TO superset_reader;
\connect wdi_db
GRANT USAGE ON SCHEMA public TO superset_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO superset_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE :"warehouse_owner" IN SCHEMA public
  GRANT SELECT ON TABLES TO superset_reader;
SQL

echo "The superset_reader role has read-only access to the WDI warehouse."
