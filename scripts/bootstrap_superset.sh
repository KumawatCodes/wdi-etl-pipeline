#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
COMPOSE_ENV="$PROJECT_ROOT/.env.compose"
[[ -r "$COMPOSE_ENV" ]] || { echo "Missing .env.compose." >&2; exit 1; }
cd "$PROJECT_ROOT"

# This one-shot profile contains the admin password and is not the web process.
docker compose --env-file "$COMPOSE_ENV" build superset superset-bootstrap
docker compose --profile bootstrap --env-file "$COMPOSE_ENV" run --rm superset-bootstrap

docker compose --env-file "$COMPOSE_ENV" up -d superset
