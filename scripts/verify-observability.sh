#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

pg_health="$(sudo -n docker inspect -f '{{.State.Health.Status}}' hermes-eos-postgres 2>/dev/null || echo missing)"
px_health="$(sudo -n docker inspect -f '{{.State.Health.Status}}' hermes-eos-phoenix 2>/dev/null || echo missing)"
echo "postgres_health=$pg_health"
echo "phoenix_health=$px_health"

# No public postgres listener
if ss -lnt | rg -q ':5432\b'; then
  echo "FAIL: host has a :5432 listener" >&2
  exit 1
fi
echo "PASS: no host :5432"

ss -lnt | rg -q '127.0.0.1:6006' && echo "PASS: phoenix loopback 6006" || echo "WARN: phoenix 6006 not listening"

# Phoenix must not be on 0.0.0.0:6006
if ss -lnt | rg -q '0.0.0.0:6006'; then
  echo "FAIL: phoenix published on 0.0.0.0:6006" >&2
  exit 1
fi

if [[ "$pg_health" != "healthy" ]]; then
  echo "FAIL: postgres not healthy" >&2
  exit 1
fi
curl -fsS -o /dev/null http://127.0.0.1:6006 || { echo "FAIL: phoenix UI"; exit 1; }
echo "PASS: phoenix UI"
if ss -lnt | rg -q '0.0.0.0:6006|:4317\b'; then
  echo "FAIL: unexpected public observability listener" >&2
  exit 1
fi
echo "PASS: verify-observability"
