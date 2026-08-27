#!/usr/bin/env bash
set -euo pipefail
# Isolated restore validation: load dumps into a throwaway postgres, never the live volume.
DUMP_DIR="${1:?usage: observability-db-verify.sh /path/to/backup-dir}"
test -f "$DUMP_DIR/phoenix.sql"
NAME="hermes-eos-restore-verify-$$"
sudo -n docker rm -f "$NAME" >/dev/null 2>&1 || true
sudo -n docker run -d --name "$NAME" \
  -e POSTGRES_PASSWORD=verify \
  postgres:16.15@sha256:f1c3376c26f2609ab9f29f71f824103fe2fcd8ee0346485cb6122a4f93df6f94 >/dev/null
cleanup() { sudo -n docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT
ready=0
for _ in $(seq 1 60); do
  if sudo -n docker exec -e PGPASSWORD=verify "$NAME" \
    psql -U postgres -c "SELECT 1" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
test "$ready" -eq 1
sudo -n docker exec -e PGPASSWORD=verify "$NAME" psql -U postgres -c "CREATE DATABASE phoenix;" >/dev/null
sudo -n docker exec -i -e PGPASSWORD=verify "$NAME" psql -v ON_ERROR_STOP=1 -U postgres -d phoenix < "$DUMP_DIR/phoenix.sql" >/tmp/hermes-eos-restore-psql.log
if grep -q 'ERROR:' /tmp/hermes-eos-restore-psql.log; then
  tail -n 20 /tmp/hermes-eos-restore-psql.log >&2
  exit 1
fi
COUNT="$(sudo -n docker exec -e PGPASSWORD=verify "$NAME" psql -U postgres -d phoenix -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema');")"
echo "restored_user_tables=$COUNT"
echo "PASS: isolated restore validation (live DB untouched)"
