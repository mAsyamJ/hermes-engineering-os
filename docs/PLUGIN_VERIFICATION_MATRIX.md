# Plugin Verification Matrix

Qualification is run with `scripts/verify-plugins.sh` in a temporary, scrubbed
home with outbound sockets denied and deterministic fake LLM results.

| Plugin | Static | Import | Register | Dashboard | Backend | Runtime | Uninstall | Final |
|---|---|---|---|---|---|---|---|---|
| example-dashboard | PASS | PASS | N/A | PASS | PASS | PASS isolated | PASS isolated | VERIFIED |
| strike-freedom-cockpit | PASS | N/A | PASS SDK VM | PASS | N/A | PASS isolated | PASS isolated | VERIFIED |
| plugin-llm-example | PASS | PASS | PASS | N/A | N/A | PASS fake LLM | PASS isolated | VERIFIED |
| plugin-llm-async-example | PASS | PASS | PASS | N/A | N/A | PASS fake async LLM | PASS isolated | VERIFIED |
| superpowers 6.3.0 | PASS | PASS | PASS | N/A | N/A | PASS hook/skills | N/A enabled | VERIFIED |
| hermes_otel 1.0 | PASS | PASS | PASS 13 hooks | PASS manifest | PASS read status | PASS fail-open OTLP | N/A enabled | VERIFIED |
| engineering-os 1.0.0 | PASS | PASS | PASS side-effect-free | PASS | PASS GET-only including `/analytics*` and `/evaluations*` | PASS live (Observability + Analytics + Evaluations) | PASS guarded | VERIFIED |

`hermes_otel` is repaired in the active Hermes venv with OpenTelemetry 1.44.x.
Missing Phoenix still fail-opens. Engineering OS `register()` stays hook-free
when Kanban env is absent (preflight) and stamps Kanban resource/span identity
when `HERMES_KANBAN_*` is present. Analytics routes proxy `127.0.0.1:9120` and
stay GET-only; sidecar outage is DEGRADED, not a Hermes failure. Evaluation
routes are likewise GET-only; candidate execution never joins the Hermes
hot path.

No matrix entry is `UNKNOWN`. Live Engineering OS results are populated after
the install/uninstall/reinstall qualification and are required by
`scripts/verify.sh`.

