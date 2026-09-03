#!/usr/bin/env bash
set -euo pipefail
# Create hermes_control on the existing unpublished Postgres. No new server. No host port.
# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
ENV="$ROOT/deploy/observability/.env"
python3 - "$ENV" <<'PY'
from pathlib import Path
import secrets
import sys
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
changed = False
for key in (
    "HERMES_CONTROL_DB_PASSWORD",
    "HERMES_CONTROL_OWNER_PASSWORD",
    "HERMES_CONTROL_OPERATOR_PASSWORD",
    "HERMES_CONTROL_READER_PASSWORD",
    "HERMES_CONTROL_RESOLVER_PASSWORD",
):
    if not any(line.startswith(key + "=") for line in text.splitlines()):
        text += f"\n{key}={secrets.token_urlsafe(24)}\n"
        changed = True
if changed:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    print("appended control role passwords")
else:
    print("control role passwords already present")
PY
set -a
# shellcheck disable=SC1090
source "$ENV"
set +a
OWNER_PASS="${HERMES_CONTROL_OWNER_PASSWORD:-$HERMES_CONTROL_DB_PASSWORD}"
sudo -n docker exec -i hermes-eos-postgres \
  psql -v ON_ERROR_STOP=1 -U eos_admin -d postgres <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='hermes_control_owner') THEN
    CREATE ROLE hermes_control_owner LOGIN PASSWORD '${OWNER_PASS}';
  ELSE
    ALTER ROLE hermes_control_owner PASSWORD '${OWNER_PASS}';
  END IF;
END\$\$;
SELECT 'create_db' WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='hermes_control');
SQL
if ! sudo -n docker exec hermes-eos-postgres psql -U eos_admin -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='hermes_control'" | grep -q 1; then
  sudo -n docker exec hermes-eos-postgres \
    psql -v ON_ERROR_STOP=1 -U eos_admin -d postgres \
    -c "CREATE DATABASE hermes_control OWNER hermes_control_owner;"
fi
sudo -n docker exec hermes-eos-postgres \
  psql -v ON_ERROR_STOP=1 -U eos_admin -d postgres \
  -c "REVOKE ALL ON DATABASE phoenix FROM PUBLIC; REVOKE ALL ON DATABASE hermes_engineering FROM PUBLIC; REVOKE ALL ON DATABASE hermes_control FROM PUBLIC; GRANT CONNECT ON DATABASE hermes_control TO hermes_control_owner;"
sudo -n docker exec -i hermes-eos-postgres \
  psql -v ON_ERROR_STOP=1 -U eos_admin -d hermes_control <<'SQL'
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO hermes_control_owner;
ALTER SCHEMA public OWNER TO hermes_control_owner;
SQL
echo "PASS: hermes_control database"
