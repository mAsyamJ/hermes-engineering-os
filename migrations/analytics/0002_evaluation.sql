-- Phase 4 derived evaluation schema. Owner: hermes_engineering.
-- Never apply to the phoenix database.

CREATE TABLE IF NOT EXISTS evaluation_profile_snapshots (
    profile_id TEXT NOT NULL,
    profile_version TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    config JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (profile_id, profile_version)
);

CREATE TABLE IF NOT EXISTS evaluator_definition_snapshots (
    evaluator_id TEXT NOT NULL,
    evaluator_version TEXT NOT NULL,
    category TEXT NOT NULL,
    sandbox_tier TEXT NOT NULL,
    impl_hash TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    spec JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (evaluator_id, evaluator_version)
);

CREATE TABLE IF NOT EXISTS evaluation_artifacts (
    artifact_id UUID PRIMARY KEY,
    repository_id TEXT,
    board TEXT,
    task_id TEXT,
    kanban_run_id BIGINT,
    method TEXT NOT NULL,
    base_commit TEXT,
    candidate_commit TEXT,
    patch_hash TEXT,
    content_hash TEXT NOT NULL,
    size_bytes BIGINT NOT NULL,
    secret_scan_status TEXT NOT NULL,
    capture_detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    storage_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (content_hash)
);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    evaluation_run_id UUID PRIMARY KEY,
    board TEXT NOT NULL,
    task_id TEXT NOT NULL,
    kanban_run_id BIGINT,
    cohort TEXT NOT NULL,
    eligibility TEXT NOT NULL,
    eligibility_reason TEXT NOT NULL,
    execution_status TEXT NOT NULL,
    contract_version TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    profile_version TEXT NOT NULL,
    profile_hash TEXT NOT NULL,
    candidate_artifact_id UUID REFERENCES evaluation_artifacts (artifact_id),
    baseline_artifact_id UUID REFERENCES evaluation_artifacts (artifact_id),
    candidate_artifact_hash TEXT,
    baseline_artifact_hash TEXT,
    trace_id TEXT,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    identity_hash TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    detail TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS evaluation_runs_identity_current
    ON evaluation_runs (identity_hash) WHERE is_current;
CREATE INDEX IF NOT EXISTS evaluation_runs_task_idx
    ON evaluation_runs (board, task_id, started_at DESC);

CREATE TABLE IF NOT EXISTS evaluation_results (
    id BIGSERIAL PRIMARY KEY,
    evaluation_run_id UUID NOT NULL REFERENCES evaluation_runs (evaluation_run_id),
    evaluator_id TEXT NOT NULL,
    evaluator_version TEXT NOT NULL,
    category TEXT NOT NULL,
    subject TEXT NOT NULL,
    verdict TEXT NOT NULL,
    sandbox_tier TEXT NOT NULL,
    command TEXT,
    exit_code INTEGER,
    duration_ms INTEGER,
    tests_discovered INTEGER,
    tests_passed INTEGER,
    tests_failed INTEGER,
    timeout BOOLEAN NOT NULL DEFAULT FALSE,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (evaluation_run_id, evaluator_id, evaluator_version, subject)
);

CREATE TABLE IF NOT EXISTS evaluation_comparisons (
    id BIGSERIAL PRIMARY KEY,
    evaluation_run_id UUID NOT NULL REFERENCES evaluation_runs (evaluation_run_id),
    evaluator_id TEXT NOT NULL,
    classification TEXT NOT NULL,
    UNIQUE (evaluation_run_id, evaluator_id)
);

CREATE TABLE IF NOT EXISTS evaluation_evidence (
    id BIGSERIAL PRIMARY KEY,
    evaluation_run_id UUID NOT NULL REFERENCES evaluation_runs (evaluation_run_id),
    kind TEXT NOT NULL,
    ref TEXT NOT NULL,
    quality TEXT NOT NULL,
    body TEXT,
    UNIQUE (evaluation_run_id, kind, ref)
);

CREATE TABLE IF NOT EXISTS evaluation_summaries (
    evaluation_run_id UUID PRIMARY KEY REFERENCES evaluation_runs (evaluation_run_id),
    summary_state TEXT NOT NULL,
    quality_vector JSONB NOT NULL,
    reason TEXT NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evaluation_projections (
    evaluation_run_id UUID PRIMARY KEY REFERENCES evaluation_runs (evaluation_run_id),
    target TEXT NOT NULL DEFAULT 'phoenix',
    status TEXT NOT NULL,
    identifier TEXT,
    detail TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evaluation_checkpoints (
    source TEXT PRIMARY KEY,
    watermark TEXT,
    source_hash TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    evaluation_run_id UUID
);

INSERT INTO schema_migrations (version) VALUES ('0002_evaluation')
ON CONFLICT (version) DO NOTHING;
