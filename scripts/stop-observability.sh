#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="$ROOT/deploy/observability/compose.yaml"
ENV="$ROOT/deploy/observability/.env"
cd "$ROOT/deploy/observability"
sudo -n docker compose --env-file "$ENV" -f "$COMPOSE" stop
echo "PASS: observability stack stopped (volumes retained)"
