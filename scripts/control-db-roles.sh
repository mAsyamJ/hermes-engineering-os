#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
ENV="$ROOT/deploy/observability/.env"
python3 - "$ENV" <<'PY'
from pathlib import Path
import secrets
import sys
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
changed = False
for key in (
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
    print("appended remaining control passwords")
else:
    print("control role passwords already present")
PY
set -a
# shellcheck disable=SC1090
source "$ENV"
set +a
sudo -n docker exec -i hermes-eos-postgres \
  psql -v ON_ERROR_STOP=1 -U eos_admin -d postgres <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='hermes_control_operator') THEN
    CREATE ROLE hermes_control_operator LOGIN PASSWORD '${HERMES_CONTROL_OPERATOR_PASSWORD}';
  ELSE
    ALTER ROLE hermes_control_operator PASSWORD '${HERMES_CONTROL_OPERATOR_PASSWORD}';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='hermes_control_reader') THEN
    CREATE ROLE hermes_control_reader LOGIN PASSWORD '${HERMES_CONTROL_READER_PASSWORD}';
  ELSE
    ALTER ROLE hermes_control_reader PASSWORD '${HERMES_CONTROL_READER_PASSWORD}';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='hermes_control_resolver') THEN
    CREATE ROLE hermes_control_resolver LOGIN PASSWORD '${HERMES_CONTROL_RESOLVER_PASSWORD}';
  ELSE
    ALTER ROLE hermes_control_resolver PASSWORD '${HERMES_CONTROL_RESOLVER_PASSWORD}';
  END IF;
END\$\$;
REVOKE ALL ON DATABASE phoenix FROM hermes_control_owner;
REVOKE ALL ON DATABASE phoenix FROM hermes_control_operator;
REVOKE ALL ON DATABASE phoenix FROM hermes_control_reader;
REVOKE ALL ON DATABASE phoenix FROM hermes_control_resolver;
REVOKE ALL ON DATABASE hermes_engineering FROM hermes_control_owner;
REVOKE ALL ON DATABASE hermes_engineering FROM hermes_control_operator;
REVOKE ALL ON DATABASE hermes_engineering FROM hermes_control_reader;
REVOKE ALL ON DATABASE hermes_engineering FROM hermes_control_resolver;
GRANT CONNECT ON DATABASE hermes_control TO hermes_control_operator;
GRANT CONNECT ON DATABASE hermes_control TO hermes_control_reader;
GRANT CONNECT ON DATABASE hermes_control TO hermes_control_resolver;
SQL
sudo -n docker exec -i hermes-eos-postgres \
  psql -v ON_ERROR_STOP=1 -U eos_admin -d hermes_control <<'SQL'
GRANT USAGE ON SCHEMA public TO hermes_control_operator;
GRANT USAGE ON SCHEMA public TO hermes_control_reader;
GRANT USAGE ON SCHEMA public TO hermes_control_resolver;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO hermes_control_operator;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO hermes_control_operator;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO hermes_control_reader;
GRANT SELECT ON adaptation_bindings, adaptation_policy_bundles, adaptation_kill_switch TO hermes_control_resolver;
ALTER DEFAULT PRIVILEGES FOR ROLE hermes_control_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO hermes_control_operator;
ALTER DEFAULT PRIVILEGES FOR ROLE hermes_control_owner IN SCHEMA public
  GRANT SELECT ON TABLES TO hermes_control_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE hermes_control_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO hermes_control_operator;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM hermes_control_operator;
REVOKE CREATE ON SCHEMA public FROM hermes_control_reader;
REVOKE CREATE ON SCHEMA public FROM hermes_control_resolver;
SQL
echo "PASS: control roles"
