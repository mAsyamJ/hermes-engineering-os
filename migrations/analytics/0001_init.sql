-- Phase 3 derived analytics schema. Owner: hermes_engineering.
-- Never apply to the phoenix database.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS source_checkpoints (
    source TEXT PRIMARY KEY,
    watermark TEXT,
    source_hash TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    materialization_id UUID
);

CREATE TABLE IF NOT EXISTS materialization_runs (
    materialization_id UUID PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    ruleset_version TEXT NOT NULL,
    mode TEXT NOT NULL,
    tasks_scanned INTEGER NOT NULL DEFAULT 0,
    tasks_changed INTEGER NOT NULL DEFAULT 0,
    tasks_unchanged INTEGER NOT NULL DEFAULT 0,
    errors INTEGER NOT NULL DEFAULT 0,
    source_watermarks JSONB NOT NULL DEFAULT '{}'::jsonb,
    partial_source_failures JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL,
    detail TEXT
);

CREATE TABLE IF NOT EXISTS task_facts (
    board TEXT NOT NULL,
    task_id TEXT NOT NULL,
    title TEXT,
    status TEXT,
    assignee TEXT,
    created_at_source BIGINT,
    started_at_source BIGINT,
    completed_at_source BIGINT,
    workspace_path TEXT,
    branch_name TEXT,
    profile TEXT,
    cohort TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    materialized_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ruleset_version TEXT NOT NULL,
    PRIMARY KEY (board, task_id)
);

CREATE TABLE IF NOT EXISTS run_facts (
    board TEXT NOT NULL,
    run_id BIGINT NOT NULL,
    task_id TEXT NOT NULL,
    profile TEXT,
    status TEXT,
    outcome TEXT,
    started_at_source BIGINT,
    ended_at_source BIGINT,
    qualifying BOOLEAN NOT NULL,
    synthetic BOOLEAN NOT NULL,
    source_hash TEXT NOT NULL,
    materialized_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (board, run_id),
    FOREIGN KEY (board, task_id) REFERENCES task_facts (board, task_id)
);

CREATE INDEX IF NOT EXISTS run_facts_task_idx ON run_facts (board, task_id);

CREATE TABLE IF NOT EXISTS trace_facts (
    trace_id TEXT PRIMARY KEY,
    board TEXT,
    task_id TEXT,
    run_id TEXT,
    session_id TEXT,
    llm_call_count INTEGER,
    tool_call_count INTEGER,
    error_count INTEGER,
    trace_wall_seconds NUMERIC,
    llm_total_seconds NUMERIC,
    tool_total_seconds NUMERIC,
    token_prompt BIGINT,
    token_completion BIGINT,
    token_total BIGINT,
    cost_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    phoenix_url TEXT,
    evidence_quality TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    materialized_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS trace_facts_task_idx ON trace_facts (board, task_id);

CREATE TABLE IF NOT EXISTS git_facts (
    board TEXT NOT NULL,
    task_id TEXT NOT NULL,
    repository_id TEXT,
    branch TEXT,
    commit_sha TEXT,
    dirty_at_observation BOOLEAN,
    evidence_quality TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    materialized_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (board, task_id),
    FOREIGN KEY (board, task_id) REFERENCES task_facts (board, task_id)
);

CREATE TABLE IF NOT EXISTS github_facts (
    board TEXT NOT NULL,
    task_id TEXT NOT NULL,
    evidence_state TEXT NOT NULL,
    pr_number INTEGER,
    pr_state TEXT,
    ci_conclusion TEXT,
    merged BOOLEAN,
    detail TEXT,
    source_hash TEXT NOT NULL,
    materialized_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (board, task_id),
    FOREIGN KEY (board, task_id) REFERENCES task_facts (board, task_id)
);

CREATE TABLE IF NOT EXISTS run_model_usage (
    board TEXT NOT NULL,
    run_id BIGINT NOT NULL,
    model TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL,
    call_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (board, run_id, model, provider, source)
);

CREATE TABLE IF NOT EXISTS run_skill_usage (
    board TEXT NOT NULL,
    run_id BIGINT NOT NULL,
    skill_name TEXT NOT NULL,
    source TEXT NOT NULL,
    call_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (board, run_id, skill_name, source)
);

CREATE TABLE IF NOT EXISTS evidence_refs (
    id BIGSERIAL PRIMARY KEY,
    board TEXT NOT NULL,
    task_id TEXT NOT NULL,
    source TEXT NOT NULL,
    kind TEXT NOT NULL,
    ref TEXT NOT NULL,
    quality TEXT NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (board, task_id, source, kind, ref)
);

CREATE TABLE IF NOT EXISTS task_outcomes (
    board TEXT NOT NULL,
    task_id TEXT NOT NULL,
    ruleset_version TEXT NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL,
    lifecycle_state TEXT NOT NULL,
    verification_state TEXT NOT NULL,
    final_outcome TEXT NOT NULL,
    first_pass_state TEXT NOT NULL,
    retry_count INTEGER,
    rework_status TEXT NOT NULL,
    rework_count INTEGER,
    human_intervention_state TEXT NOT NULL,
    task_wall_seconds NUMERIC,
    run_wall_seconds NUMERIC,
    trace_wall_seconds NUMERIC,
    llm_total_seconds NUMERIC,
    tool_total_seconds NUMERIC,
    llm_call_count INTEGER,
    tool_call_count INTEGER,
    error_count INTEGER,
    github_evidence_state TEXT NOT NULL,
    git_evidence_state TEXT NOT NULL,
    cost_status TEXT NOT NULL,
    skill_usage_status TEXT NOT NULL,
    model_usage_status TEXT NOT NULL,
    production_cohort BOOLEAN NOT NULL,
    evidence_grade TEXT NOT NULL,
    reason TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_hash TEXT NOT NULL,
    PRIMARY KEY (board, task_id),
    FOREIGN KEY (board, task_id) REFERENCES task_facts (board, task_id)
);

CREATE INDEX IF NOT EXISTS task_outcomes_final_idx ON task_outcomes (final_outcome);
CREATE INDEX IF NOT EXISTS task_outcomes_computed_idx ON task_outcomes (computed_at);

CREATE TABLE IF NOT EXISTS outcome_history (
    id BIGSERIAL PRIMARY KEY,
    board TEXT NOT NULL,
    task_id TEXT NOT NULL,
    ruleset_version TEXT NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL,
    final_outcome TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    reason TEXT
);

CREATE INDEX IF NOT EXISTS outcome_history_task_idx ON outcome_history (board, task_id, computed_at);

INSERT INTO schema_migrations (version) VALUES ('0001_init')
ON CONFLICT (version) DO NOTHING;
