# Operator Boundary Verification

Contract: read-only machine checks. The verifier never changes users, SSH,
sudoers, systemd ownership, or trust roots.

Command: `scripts/verify-operator-boundary.sh`

## Outputs

| Status | Meaning |
|---|---|
| `PASS` | Autonomous agent cannot replace enforcement or escalate to unrestricted root |
| `READY_FOR_HUMAN` | Bootstrap still required; other PAG-1 tracks may continue |
| `BLOCKED` | A production private key or similarly fatal condition exists on this host |

## Reason codes

- `AUTH_AGENT_PASSWORDLESS_ROOT` — `ubuntu` has `NOPASSWD: ALL`
- `AUTH_TRUST_ROOT_WRITABLE` — agent can write a present trust/actuator path
- `AUTH_PRIVATE_KEY_ON_AGENT_HOST` — production signing private material present
- `AUTH_NO_PROTECTED_ACTUATOR` — no protected actuation identity/unit exists
- `AUTH_NO_OPERATOR_PRINCIPAL` — no non-ubuntu administrator account
- `AUTH_VERIFIER_CODE_WRITABLE` — approval verifier source is agent-writable
- `AUTH_PROTECTED_UNIT_WRITABLE` — dispatcher/gateway unit is agent-writable
- `AUTH_GITHUB_ADMIN_ON_AGENT` — `gh` token is admin on Engineering OS
- `AUTH_GITHUB_UNPROTECTED_MAIN` — default branch has no protection
- `AUTH_PUBLIC_TRUST_IDENTITY_ABSENT` — no installed production public key

`PASS` requires that ubuntu cannot gain unrestricted root, cannot replace the
approval verifier or trust root, cannot replace a protected actuation unit,
and cannot impersonate the operator. Passwordless sudo makes `PASS`
impossible.

Human-only bootstrap remains in `.runtime/operator-bootstrap/` and
`docs/OPERATOR_BOOTSTRAP.md`. This document does not authorize executing it.
