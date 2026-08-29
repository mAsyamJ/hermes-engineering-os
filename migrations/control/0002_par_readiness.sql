-- PAR readiness metadata. Owner: hermes_control_owner.
-- Never apply to phoenix or hermes_engineering.

CREATE TABLE IF NOT EXISTS par_approval_requests (
    request_id TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL UNIQUE,
    algorithm TEXT NOT NULL,
    approval_stage TEXT NOT NULL,
    scope TEXT NOT NULL,
    policy_hash TEXT NOT NULL,
    spec JSONB NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS par_approval_nonces (
    nonce TEXT PRIMARY KEY,
    request_id TEXT,
    consumed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS par_memory_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    snapshot_hash TEXT NOT NULL,
    contract_version TEXT NOT NULL,
    spec JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS par_readiness_snapshots (
    captured_at TIMESTAMPTZ PRIMARY KEY DEFAULT NOW(),
    contract_version TEXT NOT NULL,
    cells JSONB NOT NULL
);

INSERT INTO schema_migrations (version) VALUES ('0002_par_readiness')
ON CONFLICT DO NOTHING;
