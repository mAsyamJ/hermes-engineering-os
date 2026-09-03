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
SECRET="FAKE_PHASE6_SECRET_ABC123"
EVIDENCE="$ROOT/evidence/phase6/privacy"
mkdir -p "$EVIDENCE"
echo "$SECRET" >"$EVIDENCE/plant.txt"
sudo -n docker exec hermes-eos-postgres \
  pg_dump -U eos_admin -d hermes_engineering --data-only --no-owner \
  >"$EVIDENCE/hermes_engineering.data.sql"
if grep -F "$SECRET" "$EVIDENCE/hermes_engineering.data.sql"; then
  echo "FAIL: secret in database dump" >&2
  exit 1
fi
if curl -fsS http://127.0.0.1:9120/experiments | grep -F "$SECRET"; then
  echo "FAIL: secret in API" >&2
  exit 1
fi
if git -C "$ROOT" grep -F "$SECRET" -- \
  ':!evidence/phase6/privacy/**' \
  ':!scripts/experiments/experiment-privacy-test.sh' \
  ':!tests/python/test_experiments_golden.py' \
  ':!docs/experiments/EXPERIMENT_SECURITY.md' \
  ':!docs/experiments/EXPERIMENT_CONFIGURATION_IDENTITY.md' \
  ':!SECURITY.md' >/dev/null; then
  echo "FAIL: secret committed outside privacy evidence" >&2
  exit 1
fi
PYTHONPATH="$ROOT" PYTHONDONTWRITEBYTECODE=1 \
  /home/ubuntu/.hermes/hermes-agent/venv/bin/python - <<'PY'
from engineering_os.experiments.config_snapshot import strip_secrets
value = strip_secrets({"api_key": "FAKE_PHASE6_SECRET_ABC123", "model": "x"})
assert "FAKE_PHASE6_SECRET_ABC123" not in str(value)
print("snapshot redaction PASS")
PY
echo "PASS: experiment privacy (secret not leaked)"
