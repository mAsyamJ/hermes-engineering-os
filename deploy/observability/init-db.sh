#!/bin/bash
set -euo pipefail
# Runs once on first Postgres volume init. Creates least-privilege app roles.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
CREATE ROLE phoenix LOGIN PASSWORD '${PHOENIX_DB_PASSWORD}';
CREATE DATABASE phoenix OWNER phoenix;
CREATE ROLE hermes_engineering LOGIN PASSWORD '${HERMES_ENGINEERING_DB_PASSWORD}';
CREATE DATABASE hermes_engineering OWNER hermes_engineering;
REVOKE ALL ON DATABASE phoenix FROM PUBLIC;
REVOKE ALL ON DATABASE hermes_engineering FROM PUBLIC;
GRANT CONNECT ON DATABASE phoenix TO phoenix;
GRANT CONNECT ON DATABASE hermes_engineering TO hermes_engineering;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname phoenix <<EOSQL
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO phoenix;
ALTER SCHEMA public OWNER TO phoenix;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname hermes_engineering <<EOSQL
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO hermes_engineering;
ALTER SCHEMA public OWNER TO hermes_engineering;
EOSQL
