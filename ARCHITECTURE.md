# Architecture

Canonical overview (C4, 5W+1H, live snapshot): [docs/HERMES_AGENT_OS.md](docs/HERMES_AGENT_OS.md).
This page is the short ASCII pipeline.

Hermes Engineering OS is one combined user plugin. Its gateway registration is
side-effect-free; runtime behavior lives in authenticated dashboard routes.

```text
Hermes runtime / Kanban workers
        │ observer hooks (fail-open)
        ▼
hermes-otel (pinned) --OTLP/HTTP--> Phoenix :6006 (loopback)
                                        │
                                        ▼
                              dedicated Postgres (no host port)
                                 phoenix | hermes_engineering (derived) | hermes_control (adaptation)

Hermes Kanban ──┐
profiles/runs ──┼─> read-only adapters ─> GET-only FastAPI ─> SDK IIFE
allowlisted Git ┤
GitHub API ─────┤     BLOCKED_AUTH is a valid evidence state
Phoenix GraphQL ┘     observability DEGRADED if Phoenix is down
        │
        ▼
PAR / par-v1 readiness (authority protocol, isolated spawn patch, memory harness)
        │
        ▼
PAG-1 (operator-boundary verifier, current-upstream spawn transform, real preflight)
        │
        ▼
PAG-2 (four-principal TCB, same-SHA H1, confirmatory v2, hash-locked H3
plus protected IPC plugin; production adaptation stays DISABLED)
        │
        ▼
phase3-v1 materializer (Docker oneshot, writer role)
        │
        ▼
phase4-eval-v1 evaluator (sandboxed, writer role)
        │
        ▼
phase5-perf-v1 materializer (Docker oneshot, writer role)
        │
        ▼
hermes_engineering (derived; same unpublished Postgres)
        │
        ▼
analytics sidecar :9120 (reader role) ─> Analytics / Evaluations / Performance / Experiments / Adaptation UI
```

## Authority boundaries

- Hermes owns sessions, tasks, runs, workers, scheduling, retries, profiles,
  worktrees, dispatch, and persistence.
- The canonical lifecycle identifier is `hermes.kanban.task_id`.
- Runtime task IDs, Kanban run IDs, sessions, turns, API requests, tool calls,
  Git SHAs, GitHub objects, and OTel IDs remain distinct typed dimensions.
- Correlation is emitted only from explicit metadata or unambiguous evidence.

## Read paths

- Kanban opens SQLite with `mode=ro`, `PRAGMA query_only=ON`, parameterized SQL,
  and a write-denying authorizer.
- Git commands use fixed argument vectors against `config/repositories.json`.
- GitHub CLI/API access is bounded and never reads or returns tokens.
- Plugin inventory runs in a timeout-protected subprocess; enabled plugins are
  not imported into the dashboard adapter.

## Dashboard

`dashboard/dist/index.js` is a classic IIFE using the host's
`window.__HERMES_PLUGIN_SDK__` React instance and `fetchJSON`. It provides
Overview, Tasks, Runs, Agents, Plugins, GitHub, Workspaces, Observability,
Analytics, Evaluations, Performance, Experiments, and Adaptation views plus a read-only footer slot.

## Analytics (Phase 3)

- Kanban remains canonical. `hermes_engineering` is derived and may be dropped
  without affecting Hermes.
- Phoenix is queried only through the existing GraphQL client, never internal SQL.
- Connectivity is Architecture B: analytics processes join Docker network
  `hermes-eos-observability`. Postgres has no host port. The read API is
  `hermes-eos-analytics-api` on `127.0.0.1:9120`. The materializer is a
  `docker compose run` oneshot under systemd user timer
  `hermes-eos-analytics.timer` (5 minutes).
- Ruleset `phase3-v1` never coerces UNKNOWN to FALSE. Kanban DONE is not
  verified success. GitHub `BLOCKED_AUTH` is not verification failure.
- Cost is always UNKNOWN in Phase 3. Skill usage is taken only from Phoenix
  skill spans.
- Plugin analytics routes stay GET-only and proxy the sidecar; sidecar outage
  returns DEGRADED without failing Hermes `/health`.
- Evaluation (Phase 4) is another derived layer on `hermes_engineering`.
  Candidate execution is sandboxed. Fail-open. No canonical quality score.
- Performance (Phase 5) is another derived observational layer
  (`phase5-perf-v1`). Coverage-first. No ranking, routing, or causality.
- Experiments (Phase 6) is a derived pre-registered experimentation layer
  (`phase6-exp-v1`). GET-only `/experiments*`. No auto-routing. Fixture
  qualification only; production scope disabled.
- Adaptation (Phase 7) is an isolated control plane (`phase7-adapt-v1`) in
  `hermes_control`. Recommendations, immutable policies, TEST-only approval,
  shadow, fixture canary, auto-disable, and rollback. GET-only `/adaptation*`.
  Production actuation remains DISABLED. Fail-open to Hermes; fail-closed for
  candidate policy.
- Production Adaptation Readiness (`par-v1`) adds an Ed25519 approval
  protocol (not a live human boundary), an isolated Hermes `pre_worker_spawn`
  patch that is not deployed live, a memory-snapshot harness, and a real
  MODEL experiment protocol gated on LLM budget authorization. GET-only
  `/adaptation/readiness/*` cells stay independent.

