-- Phase 7 isolated control schema. Owner: hermes_control_owner.
-- Never apply to phoenix or hermes_engineering.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS adaptation_contract_snapshots (
    contract_version TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    spec JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (contract_version, config_hash)
);

CREATE TABLE IF NOT EXISTS adaptation_recommendations (
    recommendation_id UUID PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    protocol_hash TEXT,
    conclusion TEXT NOT NULL,
    classification TEXT NOT NULL,
    state TEXT NOT NULL,
    treatment_dimension TEXT NOT NULL,
    scope TEXT NOT NULL,
    source JSONB NOT NULL,
    reason TEXT NOT NULL,
    production_promotable BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS adaptation_policy_bundles (
    policy_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    policy_hash TEXT NOT NULL UNIQUE,
    source_recommendation_id UUID REFERENCES adaptation_recommendations (recommendation_id),
    spec JSONB NOT NULL,
    candidate_config_hash TEXT NOT NULL,
    fallback_config_hash TEXT NOT NULL,
    scope TEXT NOT NULL,
    treatment_dimension TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (policy_id, policy_version, policy_hash)
);

CREATE TABLE IF NOT EXISTS adaptation_approvals (
    approval_id UUID PRIMARY KEY,
    recommendation_id UUID,
    policy_hash TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    stage TEXT NOT NULL,
    approval_class TEXT NOT NULL,
    scope TEXT NOT NULL,
    max_exposure INTEGER,
    expires_at TIMESTAMPTZ NOT NULL,
    rollback_hash TEXT NOT NULL,
    operator_identity TEXT NOT NULL,
    signature TEXT NOT NULL,
    algorithm TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS adaptation_bindings (
    binding_id UUID PRIMARY KEY,
    binding_key TEXT NOT NULL,
    policy_id TEXT,
    policy_hash TEXT,
    binding_version BIGINT NOT NULL,
    state TEXT NOT NULL,
    mode TEXT NOT NULL,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (binding_key, binding_version)
);

CREATE TABLE IF NOT EXISTS adaptation_kill_switch (
    id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    engaged BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO adaptation_kill_switch (id, engaged) VALUES (1, FALSE)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS adaptation_shadow_decisions (
    decision_id UUID PRIMARY KEY,
    policy_hash TEXT,
    task_id TEXT,
    board TEXT,
    context JSONB NOT NULL,
    result TEXT NOT NULL,
    match_reason TEXT,
    would_config_hash TEXT,
    actual_config_hash TEXT,
    conflict BOOLEAN NOT NULL DEFAULT FALSE,
    latency_ms DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS adaptation_rollout_plans (
    plan_id UUID PRIMARY KEY,
    policy_hash TEXT NOT NULL,
    spec JSONB NOT NULL,
    state TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS adaptation_exposures (
    exposure_id UUID PRIMARY KEY,
    policy_hash TEXT NOT NULL,
    unit_id TEXT NOT NULL,
    selected TEXT NOT NULL,
    candidate_config_hash TEXT,
    fallback_config_hash TEXT,
    observed_config_hash TEXT,
    fidelity TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    outcome JSONB,
    UNIQUE (policy_hash, unit_id)
);

CREATE TABLE IF NOT EXISTS adaptation_guardrail_events (
    event_id UUID PRIMARY KEY,
    policy_hash TEXT NOT NULL,
    metric_id TEXT NOT NULL,
    state TEXT NOT NULL,
    eval_window JSONB,
    evidence JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS adaptation_rollbacks (
    rollback_id UUID PRIMARY KEY,
    policy_hash TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT NOT NULL,
    trigger TEXT NOT NULL,
    reason TEXT NOT NULL,
    binding_version_before BIGINT,
    binding_version_after BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS adaptation_audit_log (
    event_id UUID PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_class TEXT NOT NULL,
    actor_identity TEXT NOT NULL,
    action TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id TEXT,
    previous_state_hash TEXT,
    new_state_hash TEXT,
    reason TEXT,
    source_evidence JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS adaptation_checkpoints (
    checkpoint_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    status TEXT,
    detail JSONB
);

CREATE INDEX IF NOT EXISTS adaptation_bindings_current_idx
    ON adaptation_bindings (binding_key, is_current);
CREATE INDEX IF NOT EXISTS adaptation_audit_occurred_idx
    ON adaptation_audit_log (occurred_at DESC);
CREATE INDEX IF NOT EXISTS adaptation_shadow_policy_idx
    ON adaptation_shadow_decisions (policy_hash);

CREATE OR REPLACE FUNCTION adaptation_reject_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'append-only table % does not allow %', TG_TABLE_NAME, TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS adaptation_audit_no_update ON adaptation_audit_log;
CREATE TRIGGER adaptation_audit_no_update
    BEFORE UPDATE OR DELETE ON adaptation_audit_log
    FOR EACH ROW EXECUTE FUNCTION adaptation_reject_mutation();

DROP TRIGGER IF EXISTS adaptation_bundles_no_update ON adaptation_policy_bundles;
CREATE TRIGGER adaptation_bundles_no_update
    BEFORE UPDATE OR DELETE ON adaptation_policy_bundles
    FOR EACH ROW EXECUTE FUNCTION adaptation_reject_mutation();

INSERT INTO schema_migrations (version) VALUES ('0001_adaptation')
ON CONFLICT DO NOTHING;
