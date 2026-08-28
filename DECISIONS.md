# Decisions

## Upstream adoption

- Official Hermes dashboard examples are copied as compatibility references.
- AI Agent Board event coalescing and Hivemind status replay are the only
  selectively modified donor logic.
- Agent Kanban remains design-only under FSL-1.1-ALv2.
- The installed `hermes_otel` plugin remains the only tracer. Engineering OS
  only stamps explicit `HERMES_KANBAN_*` values onto `OTEL_RESOURCE_ATTRIBUTES`
  and fail-open span attributes. No second exporter.

## Runtime integration

- The product is a combined user plugin. `register()` stays hook-free unless
  dispatcher Kanban env is present, in which case it stamps OTel identity.
- Backend routes are GET-only and mounted by the existing dashboard process.
- Installation uses one external symlink so repository and live bytes are
  identical.
- Built-in plugin removal is not used because its handling of external symlink
  targets is unsafe for this deployment.

## GitHub

- Local Git and GitHub evidence are separate transports.
- Missing GitHub API authentication is represented as `BLOCKED_AUTH`, not a
  failed Phase 1 build.
- Only configured repositories may be inspected; browser-supplied paths are
  rejected.

## Deferred

- Default-gateway-originated traces (`DEFAULT_GATEWAY_OTEL=DEFERRED`) until an
  operator-approved gateway restart is required.
- Interactive terminals, diff rendering, canvas editing, and lifecycle
  controls are deliberately excluded.
- Phase 4 structured evaluation (`phase4-eval-v1`): derived, sandboxed,
  quality vectors, no live LLM judge, no model ranking.

## Evaluation connectivity (Phase 4)

- Same `hermes_engineering` database. Migration `0002_evaluation`.
- Controller: compose profile `evaluate` (`evaluation-engine`).
- Candidate containers: network none, no docker.sock, no host secrets.
- Timer `hermes-eos-evaluate.timer` (advisory lock `420260827`).
- Historical production without artifacts remains INSUFFICIENT_EVIDENCE.

## Performance intelligence (Phase 5)

- Same `hermes_engineering` database. Migration `0003_performance`.
- Observational contract `phase5-perf-v1`. No automatic ranking or routing.
- Timer `hermes-eos-performance.timer` (advisory lock `520260827`).
- Zero production quality coverage is INSUFFICIENT_DATA, not 0%.

## Analytics connectivity (Phase 3)

- Dedicated `hermes_engineering` database on the observability Postgres.
- Runtime roles: owner `hermes_engineering`, writer
  `hermes_engineering_writer`, reader `hermes_engineering_reader`. Passwords
  live in gitignored `deploy/observability/.env` mode `0600`.
- Rejected: publishing Postgres, unix-socket trust from the dashboard,
  `psycopg` in the Hermes venv, and dashboard docker.sock.
- Materializer holds `pg_try_advisory_lock(320260827)`. Overlap returns
  `locked`. Checkpoints advance only after a successful run ends.

