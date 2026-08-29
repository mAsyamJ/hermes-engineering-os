# Operator Boundary Verification

Contract: read-only machine checks. The verifier never changes users, SSH,
sudoers, systemd ownership, or trust roots.

Command: `scripts/verify-operator-boundary.sh`

PAG-2 checks the **complete actuation TCB** and four principals
(`hermes-op`, `hermes-runtime`, `hermes-actuator`, `ubuntu`) plus
`SO_PEERCRED`. GitHub admin on the agent token is **recorded** and is
not a local PASS blocker (git refs are not a deployment authority).

## Outputs

| Status | Meaning |
|---|---|
| `PASS` | Four principals exist; ubuntu cannot replace enforcement or escalate to unrestricted root; production gateway runs as hermes-runtime; protected deploy-tool/actuator/runtime tree present and not agent-writable |
| `READY_FOR_HUMAN` | H1 bootstrap still required; other PAG-2 tracks may continue. **Not a fake PASS.** |
| `BLOCKED` | A production private key or similarly fatal condition exists on this host |

## Reason codes

- `AUTH_AGENT_PASSWORDLESS_ROOT` — `ubuntu` has `NOPASSWD: ALL`
- `AUTH_NO_HERMES_OP` / `AUTH_NO_HERMES_RUNTIME` / `AUTH_NO_HERMES_ACTUATOR`
- `AUTH_NO_OPERATOR_PRINCIPAL` — no non-ubuntu administrator account
- `AUTH_GATEWAY_RUNS_AS_AGENT` — production gateway identity is not hermes-runtime
- `AUTH_NO_SO_PEERCRED_ACTUATOR` — protected actuator source lacks SO_PEERCRED
- `AUTH_NO_PROTECTED_DEPLOY_TOOL` / `AUTH_NO_PROTECTED_RUNTIME_TREE`
- `AUTH_TRUST_ROOT_WRITABLE` — agent can write a present trust/actuator path
- `AUTH_CREDENTIAL_HOME_AGENT_WRITABLE` — production HERMES_HOME still writable by ubuntu
- `AUTH_PRIVATE_KEY_ON_AGENT_HOST` — production signing private material present
- `AUTH_NO_PROTECTED_ACTUATOR` — no protected actuation identity/unit exists
- `AUTH_VERIFIER_CODE_WRITABLE` — repo verifier is agent-writable (expected; PASS uses the protected copy)
- `AUTH_PROTECTED_UNIT_WRITABLE` — dispatcher/gateway **user** unit is agent-writable
- `AUTH_GITHUB_ADMIN_ON_AGENT` — recorded only
- `AUTH_GITHUB_UNPROTECTED_MAIN` — recorded only
- `AUTH_PUBLIC_TRUST_IDENTITY_ABSENT` — no installed production public key

`PASS` requires that ubuntu cannot gain unrestricted root, cannot replace
the protected verifier/trust/actuator/deploy-tool/runtime tree, cannot
impersonate hermes-runtime on the actuator socket, and that the production
gateway MainPID user is `hermes-runtime`. Passwordless sudo makes `PASS`
impossible.

Human-only bootstrap remains in `.runtime/operator-bootstrap/` and
`docs/OPERATOR_BOOTSTRAP.md`. This document does not authorize executing it.
