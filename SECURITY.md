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
- Phoenix UI and OTLP listen on `127.0.0.1:6006` only. Observability Postgres
  has no host port. DB passwords stay in `deploy/observability/.env` mode `0600`
  and are never returned by Engineering OS APIs.
- hermes-otel production yaml sets `capture_previews`,
  `capture_conversation_history`, and `capture_full_prompts` to false.
  `HERMES_OTEL_DEBUG` is not left enabled.
- Plugin preflight uses a temporary home, scrubbed environment, resource
  limits, denied IP sockets, and deterministic fake LLM responses.
- Pre-install state is copied to owner-only backup directories under
  `/var/backups/hermes-engineering-os`.

Report a suspected leak by disabling and unlinking the plugin with
`scripts/uninstall-plugin.sh`, restarting only the dashboard, and preserving
the relevant owner-only backup for investigation.

