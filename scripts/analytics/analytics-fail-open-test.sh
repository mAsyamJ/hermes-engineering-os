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
COMPOSE=(sudo -n docker compose --env-file "$ENV" -f "$ROOT/deploy/observability/compose.yaml")
DR="$ROOT/scripts/maintenance/dashboard-request.py"
EVIDENCE="$ROOT/evidence/phase3/fail-open"
mkdir -p "$EVIDENCE"

assert_core() {
  "$DR" /api/plugins/engineering-os/health --expect-status 200 --quiet
  curl -fsS http://127.0.0.1:6006/healthz >/dev/null
  test "$(ps -p 924 -o pid= | tr -d ' ')" = "924"
  test "$(ps -p 2381797 -o pid= | tr -d ' ')" = "2381797"
}

echo "=== A sidecar unavailable ==="
"${COMPOSE[@]}" stop analytics-api >/dev/null
sleep 1
assert_core
python3 "$DR" /api/plugins/engineering-os/health >"$EVIDENCE/a-health.json"
python3 "$DR" /api/plugins/engineering-os/analytics >"$EVIDENCE/a-analytics.json"
python3 - "$EVIDENCE" <<'PY'
import json
import sys
from pathlib import Path
evidence = Path(sys.argv[1])
health = json.loads(evidence.joinpath("a-health.json").read_text())["data"]
analytics = json.loads(evidence.joinpath("a-analytics.json").read_text())["data"]
assert health.get("status") == "AVAILABLE", health
assert analytics.get("status") == "DEGRADED", analytics
print("A health", health.get("status"), "analytics", analytics.get("status"))
PY
"${COMPOSE[@]}" start analytics-api >/dev/null
for _ in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:9120/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
CODE=$(curl -sS -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:9120/summary)
test "$CODE" = "405"
echo "PASS: A"

echo "=== B Phoenix unavailable to materializer ==="
BEFORE_TRACES=$(sudo -n docker exec hermes-eos-postgres psql -U hermes_engineering -d hermes_engineering -tAc \
  "SELECT COUNT(*) FROM trace_facts WHERE task_id='t_d1c34420'")
"${COMPOSE[@]}" run --rm --no-deps -e PHOENIX_BASE=http://127.0.0.1:1 \
  analytics-materialize --task t_d1c34420 --json >"$EVIDENCE/b.json" || true
python3 - "$EVIDENCE/b.json" <<'PY'
import json, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text().strip().splitlines()[-1]
payload = json.loads(text)
assert payload.get("status") in {"success", "partial"}, payload
failures = payload.get("partial_source_failures") or []
assert any(item.get("source") == "phoenix" for item in failures) or any(
    "phoenix" in json.dumps(item).lower() for item in payload.get("tasks") or []
), payload
print("B", payload.get("status"), "failures", len(failures))
PY
AFTER_TRACES=$(sudo -n docker exec hermes-eos-postgres psql -U hermes_engineering -d hermes_engineering -tAc \
  "SELECT COUNT(*) FROM trace_facts WHERE task_id='t_d1c34420'")
test "$BEFORE_TRACES" = "$AFTER_TRACES"
assert_core
echo "PASS: B last-good traces=$AFTER_TRACES"

echo "=== C GitHub BLOCKED_AUTH ==="
"${COMPOSE[@]}" run --rm --no-deps analytics-materialize --task t_d4cab17a --json >"$EVIDENCE/c.json" || true
python3 - "$EVIDENCE/c.json" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text().strip().splitlines()[-1])
task = payload["tasks"][0]
assert task["final_outcome"] == "COMPLETED_UNVERIFIED", task
print("C", task["final_outcome"])
PY
echo "PASS: C"

echo "=== D kill mid-run ==="
CKPT=$(sudo -n docker exec hermes-eos-postgres psql -U hermes_engineering -d hermes_engineering -tAc \
  "SELECT COALESCE(MAX(updated_at)::text,'none') FROM source_checkpoints")
sudo -n docker rm -f eos-analytics-kill-test >/dev/null 2>&1 || true
"${COMPOSE[@]}" run --name eos-analytics-kill-test --no-deps \
  analytics-materialize --backfill --recompute --json >"$EVIDENCE/d.json" 2>"$EVIDENCE/d.err" &
DPID=$!
sleep 8
sudo -n docker kill eos-analytics-kill-test >/dev/null 2>&1 || true
wait "$DPID" || true
sudo -n docker rm -f eos-analytics-kill-test >/dev/null 2>&1 || true
CKPT_AFTER=$(sudo -n docker exec hermes-eos-postgres psql -U hermes_engineering -d hermes_engineering -tAc \
  "SELECT COALESCE(MAX(updated_at)::text,'none') FROM source_checkpoints")
test "$CKPT" = "$CKPT_AFTER"
"$ROOT/scripts/verification/verify-analytics-data.sh" | tee "$EVIDENCE/d-quality.out"
grep -q "PASS: verify-analytics-data" "$EVIDENCE/d-quality.out"
assert_core
echo "PASS: D checkpoint unchanged ($CKPT)"

echo "=== E duplicate lock ==="
sudo -n docker exec hermes-eos-postgres psql -U hermes_engineering -d hermes_engineering \
  -c "SELECT pg_advisory_lock(320260827); SELECT pg_sleep(25); SELECT pg_advisory_unlock(320260827);" \
  >"$EVIDENCE/e-lock.log" 2>&1 &
LOCKPID=$!
sleep 2
"${COMPOSE[@]}" run --rm --no-deps analytics-materialize --task t_d1c34420 --json >"$EVIDENCE/e.json"
python3 - "$EVIDENCE/e.json" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text().strip().splitlines()[-1])
assert payload.get("status") == "locked", payload
print("E locked")
PY
wait "$LOCKPID" || true
echo "PASS: E"

echo "=== F malformed isolated row ==="
sudo -n docker exec -i hermes-eos-postgres psql -U hermes_engineering -d hermes_engineering <<'SQL'
INSERT INTO task_facts (board, task_id, title, status, cohort, source_hash, ruleset_version)
VALUES ('orphan-board', 't_orphan_quality', 'orphan', 'done', 'fixture', 'orphan', 'phase3-v1');
INSERT INTO task_outcomes (
  board, task_id, ruleset_version, computed_at, lifecycle_state, verification_state,
  final_outcome, first_pass_state, retry_count, rework_status, human_intervention_state,
  github_evidence_state, git_evidence_state, cost_status, skill_usage_status,
  model_usage_status, production_cohort, evidence_grade, reason, evidence, source_hash
) VALUES (
  'orphan-board', 't_orphan_quality', 'phase3-v1', NOW(), 'DONE', 'UNKNOWN',
  'VERIFIED_SUCCESS', 'UNKNOWN', 0, 'UNKNOWN', 'UNKNOWN',
  'UNKNOWN', 'UNKNOWN', 'UNKNOWN', 'UNKNOWN',
  'UNKNOWN', false, 'NONE', 'planted quality violation', '{}'::jsonb, 'orphan'
);
SQL
set +e
"$ROOT/scripts/verification/verify-analytics-data.sh" >"$EVIDENCE/f-quality-fail.out" 2>&1
FSTATUS=$?
set -e
test "$FSTATUS" -ne 0
grep -q "verified_success_without_pass_verification\|violations" "$EVIDENCE/f-quality-fail.out" \
  || python3 - "$EVIDENCE/f-quality-fail.out" <<'PY'
from pathlib import Path
import sys
text = Path(sys.argv[1]).read_text()
assert "FAIL" in text or "verified_success" in text, text[-1000:]
print("F quality detected planted row")
PY
sudo -n docker exec -i hermes-eos-postgres psql -U hermes_engineering -d hermes_engineering <<'SQL'
DELETE FROM task_outcomes WHERE board='orphan-board' AND task_id='t_orphan_quality';
DELETE FROM task_facts WHERE board='orphan-board' AND task_id='t_orphan_quality';
SQL
"$ROOT/scripts/verification/verify-analytics-data.sh" | tee "$EVIDENCE/f-quality-clean.out"
grep -q "PASS: verify-analytics-data" "$EVIDENCE/f-quality-clean.out"
echo "PASS: F"

assert_core
echo "PASS: analytics-fail-open A-F"
