#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV="$ROOT/deploy/observability/.env"
# shellcheck disable=SC1090
set -a
source "$ENV"
set +a
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="/var/backups/hermes-engineering-os/observability-$STAMP"
sudo install -d -o ubuntu -g ubuntu -m 0700 "$DEST"
sudo -n docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" hermes-eos-postgres \
  pg_dump -U "$POSTGRES_USER" -d phoenix --no-owner --no-privileges \
  | sudo tee "$DEST/phoenix.sql" >/dev/null
sudo -n docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" hermes-eos-postgres \
  pg_dump -U "$POSTGRES_USER" -d hermes_engineering --no-owner --no-privileges \
  | sudo tee "$DEST/hermes_engineering.sql" >/dev/null
if sudo -n docker exec hermes-eos-postgres \
  psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='hermes_control'" | grep -q 1; then
  sudo -n docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" hermes-eos-postgres \
    pg_dump -U "$POSTGRES_USER" -d hermes_control --no-owner --no-privileges \
    | sudo tee "$DEST/hermes_control.sql" >/dev/null
  sudo chown ubuntu:ubuntu "$DEST/hermes_control.sql"
  sudo chmod 0600 "$DEST/hermes_control.sql"
fi
sudo chown ubuntu:ubuntu "$DEST/phoenix.sql" "$DEST/hermes_engineering.sql"
sudo chmod 0600 "$DEST/phoenix.sql" "$DEST/hermes_engineering.sql"
# readability check without restoring
python3 - "$DEST" <<'PY'
from pathlib import Path
import sys
dest = Path(sys.argv[1])
for name in ("phoenix.sql", "hermes_engineering.sql"):
    path = dest / name
    if not path.is_file():
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    assert "PostgreSQL database dump" in text, name
control = dest / "hermes_control.sql"
if control.is_file():
    text = control.read_text(encoding="utf-8", errors="replace")
    assert "PostgreSQL database dump" in text, "hermes_control.sql"
print("readable", dest)
PY
echo "PASS: backup $DEST"
