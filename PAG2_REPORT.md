# PAG-2 Report

Contract: `par-v1` / `pag1-v1` remain valid. PAG-2 does **not** enable
unrestricted production adaptation. Auto-promote remains absent.

Captured HEAD: local `8652f98` (and later local commits). **Not pushed.**

## Status (live machine)

| Gate | Status |
|---|---|
| PAG2-0 autonomous hardening | PASS |
| H1 four-principal same-SHA cutover | **READY_FOR_HUMAN** — not faked |
| H2 confirmatory experiment budget | READY_FOR_BUDGET_AUTHORIZATION |
| H3 hash-locked live spawn-transform | NOT_DEPLOYED |
| Real evidence | BLOCKED_BUDGET |
| Production shadow | BLOCKED_EVIDENCE |
| Approval A / one-task canary | BLOCKED_SECURITY_BOUNDARY |
| Production adaptation | DISABLED |

`scripts/verify-operator-boundary.sh` = `READY_FOR_HUMAN` with
`AUTH_AGENT_PASSWORDLESS_ROOT`, `AUTH_NO_HERMES_OP`,
`AUTH_NO_HERMES_RUNTIME`, `AUTH_NO_HERMES_ACTUATOR`,
`AUTH_GATEWAY_RUNS_AS_AGENT`. PASS is impossible until H1.

## Autonomous work already on this tree

- Isolated live patch QUALIFIED at SHA256
  `51d4dd4d003143cdfea07d53668e8079f6d5163dc0a2777b3d5c3efd0001ecd4`
  against exact live SHA `c0106e50`. No ThreadPoolExecutor. Production
  tree unpatched.
- Confirmatory freeze `real-model-sol-vs-terra-v2`: 28 pairs / 56 units.
  Protocol hash `fa1b83d8583f832ac8ed15f456f12f9856aca1b26689d8859f1d6e5a7e3a870a`.
  v1 is PILOT_ONLY.
- HARD vs SOFT vs UNAVAILABLE classified; `-Q` does not cap turns;
  `--max-turns` is HARD; per-unit subprocess timeout is HARD.
- Actuator: SO_PEERCRED, caller authority stripped, atomic no-refund
  reservation, 50ms OS socket timeout.
- Deploy-tool: hash-locked; git refs rejected; `install`/`rollback`
  refused for ubuntu.
- System unit templates in `deploy/pag2/` — not installed.
- RetroPick `a8edf7dd…` and Android `e962490…` unchanged.

## Stop lines still in force

Do not fake H1 PASS. Do not paste production private keys. Do not apply
the live patch until H3. Do not run paid LLM units until H2. Do not push.
