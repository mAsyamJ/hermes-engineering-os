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
| hermes_otel 1.0 | PASS | PASS | DEGRADED expected | PASS manifest | PASS read status | dependency-degraded | N/A enabled | VERIFIED_EXTERNAL_DEP |
| engineering-os 1.0.0 | PASS | PASS | PASS side-effect-free | PASS | PASS GET-only | PASS live | PASS guarded | VERIFIED |

`hermes_otel` is intentionally not repaired in Phase 1. Its no-hook state is
caused by missing OpenTelemetry packages in the active Hermes environment and
is the approved Phase 2 repair semantic.

No matrix entry is `UNKNOWN`. Live Engineering OS results are populated after
the install/uninstall/reinstall qualification and are required by
`scripts/verify.sh`.

