#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
SECRET="FAKE_PHASE3_SECRET_ABC123"
EVIDENCE="$ROOT/evidence/phase3/privacy"
mkdir -p "$EVIDENCE"
FIXTURE_DB="/home/ubuntu/.hermes/kanban/boards/eos-phase2-obs/kanban.db"
test -f "$FIXTURE_DB"

python3 - "$FIXTURE_DB" "$SECRET" "$EVIDENCE" <<'PY'
import sqlite3
import sys
from pathlib import Path
db, secret, evidence = sys.argv[1], sys.argv[2], Path(sys.argv[3])
connection = sqlite3.connect(db, timeout=30)
connection.row_factory = sqlite3.Row
cols = [row["name"] for row in connection.execute("PRAGMA table_info(tasks)")]
body_col = "body" if "body" in cols else ("description" if "description" in cols else None)
if body_col is None:
    raise SystemExit(f"no body column in tasks: {cols}")
row = connection.execute("SELECT id, " + body_col + " FROM tasks WHERE id='t_ce5ca4b3'").fetchone()
if row is None:
    raise SystemExit("missing fixture task t_ce5ca4b3")
original = row[1] or ""
evidence.joinpath("original-body.txt").write_text(original)
connection.execute(
    f"UPDATE tasks SET {body_col} = ? WHERE id='t_ce5ca4b3'",
    (original + "\n" + secret,),
)
connection.commit()
connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
connection.close()
evidence.joinpath("planted.txt").write_text(f"column={body_col}\n")
print("planted in", body_col)
PY
sleep 1

restore_body() {
  python3 - "$FIXTURE_DB" "$EVIDENCE" <<'PY'
import sqlite3, sys
from pathlib import Path
db = sys.argv[1]
original_path = Path(sys.argv[2], "original-body.txt")
if not original_path.is_file():
    raise SystemExit(0)
original = original_path.read_text()
connection = sqlite3.connect(db, timeout=30)
cols = [row[1] for row in connection.execute("PRAGMA table_info(tasks)")]
body_col = "body" if "body" in cols else "description"
connection.execute(f"UPDATE tasks SET {body_col} = ? WHERE id='t_ce5ca4b3'", (original,))
connection.commit()
connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
connection.close()
print("restored fixture body")
PY
}
trap restore_body EXIT

"$ROOT/scripts/analytics/analytics-materialize.sh" --task t_ce5ca4b3 --json \
  >"$EVIDENCE/materialize.json" 2>"$EVIDENCE/materialize.err"

python3 - "$ROOT" "$SECRET" "$EVIDENCE" "$FIXTURE_DB" <<'PY'
import json, os, subprocess, sys, urllib.request
from pathlib import Path
root = Path(sys.argv[1])
secret = sys.argv[2]
evidence = Path(sys.argv[3])
fixture_db = Path(sys.argv[4])
leaks = []

dump = subprocess.check_output(
    [
        "sudo", "-n", "docker", "exec", "hermes-eos-postgres",
        "psql", "-U", "hermes_engineering", "-d", "hermes_engineering", "-Atc",
        "SELECT COUNT(*) FROM task_outcomes WHERE reason LIKE '%FAKE_PHASE3%' OR source_hash LIKE '%FAKE_PHASE3%';",
    ],
    text=True,
).strip()
full = subprocess.check_output(
    [
        "sudo", "-n", "docker", "exec", "hermes-eos-postgres",
        "pg_dump", "-U", "eos_admin", "-d", "hermes_engineering", "--data-only", "--no-owner",
    ],
    text=True,
    errors="replace",
)
evidence.joinpath("db-dump-scan.txt").write_text(f"count_reason={dump}\n")
if secret in full:
    leaks.append("analytics_db")

for path in (
    "http://127.0.0.1:9120/summary",
    "http://127.0.0.1:9120/tasks?cohort=all&limit=200",
    "http://127.0.0.1:9120/tasks/t_ce5ca4b3?board=eos-phase2-obs",
):
    try:
        body = urllib.request.urlopen(path, timeout=8).read().decode("utf-8", "replace")
    except Exception as exc:
        body = f"{type(exc).__name__}: {exc}"
    evidence.joinpath("api-" + path.split("/")[-1].split("?")[0] + ".json").write_text(body[:20000])
    if secret in body:
        leaks.append(path)

sys.path.insert(0, str(root))
from engineering_os.analytics import adapters
from engineering_os.analytics.normalize import strip_task
task = adapters.read_task("eos-phase2-obs", "t_ce5ca4b3")
comments = adapters.read_comment_authors("eos-phase2-obs", "t_ce5ca4b3")
stripped = strip_task(task or {})
adapter_blob = json.dumps({"task": stripped, "comments": comments}, default=str)
evidence.joinpath("adapter.json").write_text(adapter_blob)
if secret in adapter_blob:
    leaks.append("normalized_adapter")

log_text = evidence.joinpath("materialize.json").read_text(errors="replace")
log_text += evidence.joinpath("materialize.err").read_text(errors="replace")
if secret in log_text:
    leaks.append("materializer_logs")

# git tracked files excluding this privacy script
tracked = subprocess.check_output(["git", "-C", str(root), "ls-files"], text=True).splitlines()
for rel in tracked:
    if rel.endswith("analytics-privacy-test.sh"):
        continue
    text = (root / rel).read_text(errors="replace") if (root / rel).is_file() else ""
    if secret in text:
        leaks.append(f"git:{rel}")

env_path = root / "deploy/observability/.env"
if env_path.is_file():
    ignored = subprocess.check_output(
        ["git", "-C", str(root), "check-ignore", "-v", str(env_path)],
        text=True,
        errors="replace",
    )
    evidence.joinpath("env-ignore.txt").write_text(ignored)
    if not ignored.strip():
        leaks.append("env_not_gitignored")

print("leaks=" + (",".join(leaks) if leaks else "none"))
evidence.joinpath("leaks.txt").write_text("\n".join(leaks) or "none\n")
if leaks:
    raise SystemExit(1)
print("PASS: analytics-privacy-test")
PY

echo "PASS: analytics-privacy-test"
