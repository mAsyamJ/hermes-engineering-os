-- Phase 5 derived performance schema. Owner: hermes_engineering.
-- Never apply to the phoenix database. Do not duplicate Phase 3/4 facts.

CREATE TABLE IF NOT EXISTS performance_contract_snapshots (
    contract_version TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    spec JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (contract_version, config_hash)
);

CREATE TABLE IF NOT EXISTS performance_cohort_snapshots (
    cohort_id TEXT NOT NULL,
    cohort_version TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    definition JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (cohort_id, cohort_version, config_hash)
);

CREATE TABLE IF NOT EXISTS performance_metric_definitions (
    metric_id TEXT NOT NULL,
    definition_version TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    spec JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (metric_id, definition_version, config_hash)
);

CREATE TABLE IF NOT EXISTS performance_materialization_runs (
    materialization_id UUID PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    contract_version TEXT NOT NULL,
    phase3_ruleset_version TEXT,
    phase4_contract_version TEXT,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    cohorts_scanned INTEGER NOT NULL DEFAULT 0,
    aggregates_written INTEGER NOT NULL DEFAULT 0,
    comparisons_written INTEGER NOT NULL DEFAULT 0,
    errors INTEGER NOT NULL DEFAULT 0,
    detail TEXT,
    source_hash TEXT
);

CREATE TABLE IF NOT EXISTS performance_aggregates (
    aggregate_id UUID PRIMARY KEY,
    materialization_id UUID REFERENCES performance_materialization_runs (materialization_id),
    contract_version TEXT NOT NULL,
    phase3_ruleset_version TEXT NOT NULL,
    phase4_contract_version TEXT,
    cohort_id TEXT NOT NULL,
    cohort_version TEXT NOT NULL,
    cohort_hash TEXT NOT NULL,
    dimension_type TEXT NOT NULL,
    dimension_value TEXT NOT NULL,
    metric_id TEXT NOT NULL,
    population_n INTEGER NOT NULL,
    known_n INTEGER NOT NULL,
    unknown_n INTEGER NOT NULL,
    na_n INTEGER NOT NULL DEFAULT 0,
    coverage NUMERIC,
    value NUMERIC,
    unit TEXT,
    uncertainty JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence_tier TEXT NOT NULL,
    interpretation TEXT,
    source_hash TEXT NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    extras JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE UNIQUE INDEX IF NOT EXISTS performance_aggregates_identity_current
    ON performance_aggregates (
        contract_version, cohort_id, cohort_version, cohort_hash,
        dimension_type, dimension_value, metric_id
    ) WHERE is_current;

CREATE INDEX IF NOT EXISTS performance_aggregates_metric_idx
    ON performance_aggregates (metric_id, computed_at DESC);

CREATE TABLE IF NOT EXISTS performance_comparisons (
    comparison_id UUID PRIMARY KEY,
    materialization_id UUID REFERENCES performance_materialization_runs (materialization_id),
    comparison_set TEXT NOT NULL,
    contract_version TEXT NOT NULL,
    metric_id TEXT NOT NULL,
    left_aggregate_id UUID REFERENCES performance_aggregates (aggregate_id),
    right_aggregate_id UUID REFERENCES performance_aggregates (aggregate_id),
    left_identity TEXT NOT NULL,
    right_identity TEXT NOT NULL,
    left_n INTEGER,
    right_n INTEGER,
    left_estimate NUMERIC,
    right_estimate NUMERIC,
    absolute_difference NUMERIC,
    relative_difference NUMERIC,
    uncertainty JSONB NOT NULL DEFAULT '{}'::jsonb,
    coverage JSONB NOT NULL DEFAULT '{}'::jsonb,
    left_tier TEXT,
    right_tier TEXT,
    comparability TEXT NOT NULL,
    confounding_status TEXT NOT NULL,
    interpretation TEXT NOT NULL,
    strata JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS performance_comparisons_set_idx
    ON performance_comparisons (comparison_set, metric_id, computed_at DESC);

CREATE TABLE IF NOT EXISTS performance_insights (
    insight_id UUID PRIMARY KEY,
    materialization_id UUID REFERENCES performance_materialization_runs (materialization_id),
    comparison_id UUID REFERENCES performance_comparisons (comparison_id),
    aggregate_id UUID REFERENCES performance_aggregates (aggregate_id),
    kind TEXT NOT NULL,
    body TEXT NOT NULL,
    causal BOOLEAN NOT NULL DEFAULT FALSE,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS performance_checkpoints (
    source TEXT PRIMARY KEY,
    watermark TEXT,
    source_hash TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    materialization_id UUID
);

INSERT INTO schema_migrations (version) VALUES ('0003_performance')
ON CONFLICT (version) DO NOTHING;
