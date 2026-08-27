#!/usr/bin/env bash
set -euo pipefail
# Create least-privilege analytics roles. Never touch the phoenix database objects.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
ENV="$ROOT/deploy/observability/.env"
python3 - "$ENV" <<'PY'
from pathlib import Path
import secrets
import sys
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
changed = False
for key in ("HERMES_ENGINEERING_WRITER_PASSWORD", "HERMES_ENGINEERING_READER_PASSWORD"):
    if not any(line.startswith(key + "=") for line in text.splitlines()):
        text += f"\n{key}={secrets.token_urlsafe(24)}\n"
        changed = True
if changed:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    print("appended analytics role passwords")
else:
    print("analytics role passwords already present")
PY
# shellcheck disable=SC1090
set -a
source "$ENV"
set +a

sudo -n docker exec hermes-eos-postgres \
  psql -v ON_ERROR_STOP=1 -U eos_admin -d postgres \
  -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='hermes_engineering_writer') THEN CREATE ROLE hermes_engineering_writer LOGIN PASSWORD '$HERMES_ENGINEERING_WRITER_PASSWORD'; ELSE ALTER ROLE hermes_engineering_writer PASSWORD '$HERMES_ENGINEERING_WRITER_PASSWORD'; END IF; END\$\$;"
sudo -n docker exec hermes-eos-postgres \
  psql -v ON_ERROR_STOP=1 -U eos_admin -d postgres \
  -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='hermes_engineering_reader') THEN CREATE ROLE hermes_engineering_reader LOGIN PASSWORD '$HERMES_ENGINEERING_READER_PASSWORD'; ELSE ALTER ROLE hermes_engineering_reader PASSWORD '$HERMES_ENGINEERING_READER_PASSWORD'; END IF; END\$\$;"

sudo -n docker exec hermes-eos-postgres \
  psql -v ON_ERROR_STOP=1 -U eos_admin -d postgres -c \
  "REVOKE ALL ON DATABASE phoenix FROM hermes_engineering_writer; REVOKE ALL ON DATABASE phoenix FROM hermes_engineering_reader; GRANT CONNECT ON DATABASE hermes_engineering TO hermes_engineering_writer; GRANT CONNECT ON DATABASE hermes_engineering TO hermes_engineering_reader;"

sudo -n docker exec -i hermes-eos-postgres \
  psql -v ON_ERROR_STOP=1 -U eos_admin -d hermes_engineering <<'SQL'
GRANT USAGE ON SCHEMA public TO hermes_engineering_writer;
GRANT USAGE ON SCHEMA public TO hermes_engineering_reader;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO hermes_engineering_writer;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO hermes_engineering_writer;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO hermes_engineering_reader;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO hermes_engineering_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE hermes_engineering IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO hermes_engineering_writer;
ALTER DEFAULT PRIVILEGES FOR ROLE hermes_engineering IN SCHEMA public
  GRANT SELECT ON TABLES TO hermes_engineering_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE hermes_engineering IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO hermes_engineering_writer;
ALTER DEFAULT PRIVILEGES FOR ROLE hermes_engineering IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO hermes_engineering_reader;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM hermes_engineering_writer;
REVOKE CREATE ON SCHEMA public FROM hermes_engineering_reader;
SQL
echo "PASS: analytics roles"
