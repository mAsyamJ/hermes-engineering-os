-- Phase 6 derived experiment schema. Owner: hermes_engineering.
-- Never apply to the phoenix database. Do not duplicate Phase 3/4/5 facts.

CREATE TABLE IF NOT EXISTS experiment_contract_snapshots (
    contract_version TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    spec JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (contract_version, config_hash)
);

CREATE TABLE IF NOT EXISTS experiment_definitions (
    experiment_id TEXT NOT NULL,
    definition_version TEXT NOT NULL,
    definition_hash TEXT NOT NULL,
    source_path TEXT,
    spec JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, definition_version, definition_hash)
);

CREATE TABLE IF NOT EXISTS experiment_protocol_versions (
    protocol_id UUID PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    protocol_version TEXT NOT NULL,
    pre_registration_hash TEXT NOT NULL UNIQUE,
    definition_hash TEXT NOT NULL,
    state TEXT NOT NULL,
    scope TEXT NOT NULL,
    design TEXT NOT NULL,
    treatment_dimension TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    primary_metric JSONB NOT NULL,
    secondary_metrics JSONB NOT NULL DEFAULT '[]'::jsonb,
    guardrails JSONB NOT NULL,
    sample_plan JSONB NOT NULL,
    analysis_plan JSONB NOT NULL,
    assignment_plan JSONB NOT NULL,
    budget JSONB NOT NULL,
    missingness JSONB NOT NULL,
    seed TEXT NOT NULL,
    assignment_algorithm_version TEXT NOT NULL,
    control_variant_id TEXT NOT NULL,
    candidate_variant_id TEXT NOT NULL,
    control_config_hash TEXT NOT NULL,
    candidate_config_hash TEXT NOT NULL,
    environment_hash TEXT NOT NULL,
    phase3_ruleset TEXT NOT NULL,
    phase4_contract TEXT NOT NULL,
    phase5_contract TEXT NOT NULL,
    phase6_contract TEXT NOT NULL,
    spec JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    frozen_at TIMESTAMPTZ,
    UNIQUE (experiment_id, protocol_version)
);

CREATE TABLE IF NOT EXISTS experiment_config_snapshots (
    config_snapshot_id UUID PRIMARY KEY,
    protocol_id UUID NOT NULL REFERENCES experiment_protocol_versions (protocol_id),
    variant_id TEXT NOT NULL,
    variant_role TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS experiment_units (
    protocol_id UUID NOT NULL REFERENCES experiment_protocol_versions (protocol_id),
    unit_id TEXT NOT NULL,
    case_id TEXT,
    pair_id TEXT,
    stratum TEXT,
    benchmark_id TEXT,
    repo_base_sha TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (protocol_id, unit_id)
);

CREATE TABLE IF NOT EXISTS experiment_assignments (
    assignment_id UUID PRIMARY KEY,
    protocol_id UUID NOT NULL REFERENCES experiment_protocol_versions (protocol_id),
    unit_id TEXT NOT NULL,
    variant_id TEXT NOT NULL,
    variant_role TEXT NOT NULL,
    stratum TEXT,
    pair_id TEXT,
    seed TEXT NOT NULL,
    assignment_algorithm_version TEXT NOT NULL,
    assignment_hash TEXT NOT NULL,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    execution_started_at TIMESTAMPTZ,
    UNIQUE (protocol_id, unit_id)
);

CREATE TABLE IF NOT EXISTS experiment_exposures (
    exposure_id UUID PRIMARY KEY,
    protocol_id UUID NOT NULL REFERENCES experiment_protocol_versions (protocol_id),
    unit_id TEXT NOT NULL,
    assigned_variant_id TEXT NOT NULL,
    assigned_variant_role TEXT NOT NULL,
    observed_config_hash TEXT,
    fidelity TEXT NOT NULL,
    itt_variant_role TEXT NOT NULL,
    reassigned BOOLEAN NOT NULL DEFAULT FALSE,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (protocol_id, unit_id)
);

CREATE TABLE IF NOT EXISTS experiment_observations (
    observation_id UUID PRIMARY KEY,
    protocol_id UUID NOT NULL REFERENCES experiment_protocol_versions (protocol_id),
    unit_id TEXT NOT NULL,
    metric_id TEXT NOT NULL,
    role TEXT NOT NULL,
    value TEXT,
    known BOOLEAN,
    evaluation_run_id UUID,
    source_versions JSONB NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (protocol_id, unit_id, metric_id)
);

CREATE TABLE IF NOT EXISTS experiment_analysis_runs (
    analysis_run_id UUID PRIMARY KEY,
    protocol_id UUID NOT NULL REFERENCES experiment_protocol_versions (protocol_id),
    analysis_version TEXT NOT NULL,
    analysis_hash TEXT NOT NULL,
    population TEXT NOT NULL,
    status TEXT NOT NULL,
    final BOOLEAN NOT NULL DEFAULT FALSE,
    blocked_reason TEXT,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    detail JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS experiment_results (
    result_id UUID PRIMARY KEY,
    analysis_run_id UUID REFERENCES experiment_analysis_runs (analysis_run_id),
    protocol_id UUID NOT NULL REFERENCES experiment_protocol_versions (protocol_id),
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    primary_metric TEXT NOT NULL,
    itt_n_control INTEGER,
    itt_n_candidate INTEGER,
    known_n INTEGER,
    missing_n INTEGER,
    effect_estimate NUMERIC,
    uncertainty JSONB NOT NULL DEFAULT '{}'::jsonb,
    conclusion TEXT NOT NULL,
    reason TEXT,
    validity JSONB NOT NULL DEFAULT '{}'::jsonb,
    guardrail_state TEXT,
    assignment_integrity TEXT,
    treatment_fidelity TEXT,
    source_versions JSONB NOT NULL,
    extras JSONB NOT NULL DEFAULT '{}'::jsonb,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS experiment_results_identity_current
    ON experiment_results (protocol_id) WHERE is_current;

CREATE TABLE IF NOT EXISTS experiment_guardrail_events (
    event_id UUID PRIMARY KEY,
    protocol_id UUID NOT NULL REFERENCES experiment_protocol_versions (protocol_id),
    unit_id TEXT,
    metric_id TEXT,
    state TEXT NOT NULL,
    reason TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS experiment_amendments (
    amendment_id UUID PRIMARY KEY,
    protocol_id UUID NOT NULL REFERENCES experiment_protocol_versions (protocol_id),
    reason TEXT NOT NULL,
    outcomes_already_observed BOOLEAN NOT NULL DEFAULT FALSE,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS experiment_checkpoints (
    source TEXT PRIMARY KEY,
    watermark TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS experiment_contamination_events (
    event_id UUID PRIMARY KEY,
    protocol_id UUID NOT NULL REFERENCES experiment_protocol_versions (protocol_id),
    kind TEXT NOT NULL,
    state TEXT NOT NULL,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS experiment_drift_events (
    event_id UUID PRIMARY KEY,
    protocol_id UUID NOT NULL REFERENCES experiment_protocol_versions (protocol_id),
    dimension TEXT NOT NULL,
    previous_hash TEXT,
    current_hash TEXT,
    state TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO schema_migrations (version) VALUES ('0004_experiments');

