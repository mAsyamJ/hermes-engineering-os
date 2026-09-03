#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
ENV="$ROOT/deploy/observability/.env"
SECRET="FAKE_PHASE7_SECRET_ABC123"
EVIDENCE="$ROOT/evidence/phase7/privacy"
mkdir -p "$EVIDENCE"
# shellcheck disable=SC1090
set -a
source "$ENV"
set +a
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="/tmp/eos-phase7-privacy-$STAMP"
sudo -n docker exec hermes-eos-postgres \
  pg_dump -U eos_admin -d hermes_control --no-owner --no-privileges \
  > "$EVIDENCE/hermes_control.data.sql"
chmod 600 "$EVIDENCE/hermes_control.data.sql"
curl -fsS http://127.0.0.1:9120/adaptation > "$EVIDENCE/adaptation-api.json" || true
python3 - "$ROOT" "$SECRET" "$EVIDENCE" <<'PY'
import sys
from pathlib import Path
root = Path(sys.argv[1])
secret = sys.argv[2]
evidence = Path(sys.argv[3])
haystacks = [
    evidence / "hermes_control.data.sql",
    evidence / "adaptation-api.json",
]
for path in haystacks:
    if path.is_file() and secret in path.read_text(encoding="utf-8", errors="replace"):
        raise SystemExit(f"FAIL: secret in {path}")
# Git-tracked policies and docs
for path in (root / "policies" / "adaptation").glob("*.yaml"):
    if secret in path.read_text(encoding="utf-8", errors="replace"):
        raise SystemExit(f"FAIL: secret in {path}")
print("PASS: secret absent from dumps/API/policies")
PY
echo "PASS: adaptation-privacy-test"
