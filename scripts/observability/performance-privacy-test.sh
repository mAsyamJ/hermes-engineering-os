#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
ENV="$ROOT/deploy/observability/.env"
# shellcheck disable=SC1090
set -a
source "$ENV"
set +a
SECRET="FAKE_PHASE5_SECRET_ABC123"
EVIDENCE="$ROOT/evidence/phase5/privacy"
mkdir -p "$EVIDENCE"
echo "$SECRET" >"$EVIDENCE/plant.txt"
# Secret must not appear in derived tables, dumps, or API.
sudo -n docker exec hermes-eos-postgres \
  pg_dump -U eos_admin -d hermes_engineering --data-only --no-owner \
  >"$EVIDENCE/hermes_engineering.data.sql"
if grep -F "$SECRET" "$EVIDENCE/hermes_engineering.data.sql"; then
  echo "FAIL: secret in database dump" >&2
  exit 1
fi
if curl -fsS http://127.0.0.1:9120/performance/summary | grep -F "$SECRET"; then
  echo "FAIL: secret in API" >&2
  exit 1
fi
if git -C "$ROOT" grep -F "$SECRET" -- ':!evidence/phase5/privacy/**' ':!scripts/observability/performance-privacy-test.sh' >/dev/null; then
  echo "FAIL: secret committed outside privacy evidence" >&2
  exit 1
fi
echo "PASS: performance privacy (secret not leaked)"
