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
sudo chown ubuntu:ubuntu "$DEST/phoenix.sql" "$DEST/hermes_engineering.sql"
sudo chmod 0600 "$DEST/phoenix.sql" "$DEST/hermes_engineering.sql"
# readability check without restoring
python3 - "$DEST" <<'PY'
from pathlib import Path
import sys
dest = Path(sys.argv[1])
for name in ("phoenix.sql", "hermes_engineering.sql"):
    text = (dest / name).read_text(encoding="utf-8", errors="replace")
    assert "PostgreSQL database dump" in text, name
print("readable", dest)
PY
echo "PASS: backup $DEST"
