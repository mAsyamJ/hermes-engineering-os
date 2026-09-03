# Security Model

- Dashboard and plugin APIs remain bound to `127.0.0.1:9119`.
- Hermes session authentication protects every plugin API route. The browser
  uses SDK `fetchJSON`; product code never reads the session token directly.
- The backend declares no POST, PUT, PATCH, or DELETE route.
- Kanban SQLite is opened read-only with query-only mode and a write-denying
  authorizer.
- Repository paths come only from an explicit local allowlist. Git is invoked
  with fixed argument arrays and no shell interpolation.
- GitHub tokens are neither loaded by product code nor included in API output.
- Recursive redaction covers token, secret, password, authorization, key,
  cookie, and credential fields plus common token value formats.
- Adapter failures and OTel/Phoenix/Postgres unavailability degrade
  observability evidence without affecting Hermes execution.
- Analytics sidecar or `hermes_engineering` unavailability degrades
  `/analytics*`, `/evaluations*`, `/performance*`, `/experiments*`, and
  `/adaptation*` to `DEGRADED` without affecting Hermes `/health`.
- Candidate evaluation containers have network disabled, no Docker socket, and
  no host secrets. Planted `FAKE_PHASE4_SECRET_ABC123` must not leak.
- Performance tables store IDs and aggregates only. The Phase 5 privacy plant
  from `scripts/observability/performance-privacy-test.sh` must not leak.
- Adaptation control state lives in `hermes_control`. The Phase 7 privacy plant
  `FAKE_PHASE7_SECRET_ABC123` must not leak. TEST approval signatures are not
  returned by `/adaptation/audit`. Production approval is BLOCKED_CAPABILITY.
- PAR plants `FAKE_PAR_SECRET_ABC123`. PAG-1 plants `FAKE_PAG1_SECRET_ABC123`
  and `FAKE_PAG1_APPROVAL_SECRET_ABC123` in tests only. They must not appear
  in memory snapshots, approval packages, or API output. `approval-ed25519-v1`
  is protocol scaffolding only. No production signing private key may exist on an
  agent-readable filesystem. Operator bootstrap is human-only.
- PAG-2 plants `FAKE_PAG2_SECRET_ABC123` in tests only. Four-principal TCB and
  SO_PEERCRED are required before any production grant. Ubuntu cannot run
  deploy-tool `install`/`rollback`. An agent-writable Approval A file is not
  a grant. The spawn IPC client must load from the protected runtime plugin,
  not `~/.hermes/plugins/engineering-os`. A signed Approval A grant must
  bind runtime identity; unsigned or agent-writable files are not grants.
  Canary bind is hermes-op only.
- Phoenix UI and OTLP listen on `127.0.0.1:6006` only. Observability Postgres
  has no host port. Analytics API listens on `127.0.0.1:9120` only. DB
  passwords stay in `deploy/observability/.env` mode `0600` and are never
  returned by Engineering OS APIs.
- Analytics stores metadata and evidence references, not task bodies, comment
  bodies, span `input.value`/`output.value`, tokens, or provider secrets.
- hermes-otel production yaml sets `capture_previews`,
  `capture_conversation_history`, and `capture_full_prompts` to false.
  `HERMES_OTEL_DEBUG` is not left enabled.
- Plugin preflight uses a temporary home, scrubbed environment, resource
  limits, denied IP sockets, and deterministic fake LLM responses.
- Pre-install state is copied to owner-only backup directories under
  `/var/backups/hermes-engineering-os`.

Report a suspected leak by disabling and unlinking the plugin with
`scripts/deployment/uninstall-plugin.sh`, restarting only the dashboard, and preserving
the relevant owner-only backup for investigation.

