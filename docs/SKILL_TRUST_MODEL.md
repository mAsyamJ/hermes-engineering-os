# Skill Trust Model

Defined in `agent_os/policies/trust-policy.yaml`.

| Tier | Label | Auto install |
|---|---|---|
| T0 | Local system / Agent OS | Yes if safe |
| T1 | Hermes bundled/official | Yes if safe |
| T2 | Curated allowlisted | Yes only if allowlisted **and** `should_allow_install(..., force=False)` is True |
| T3 | Community | Discover/inspect/rank only — **no** auto-install |
| T4 | Rejected/dangerous | Never |

Rules:

- Never pass `--force`.
- Dangerous verdicts never install.
- `ask` scan outcomes are not auto-install.
- Map Hermes `builtin|trusted|community` via policy `hermes_trust_map`.
