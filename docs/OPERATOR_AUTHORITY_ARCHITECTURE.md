# Operator Authority Architecture

## Options evaluated

### OPTION A — Privilege-separated local authority

A root-owned verifier and actuator user on this VPS.

**Feasibility now:** insecure. `ubuntu` has `NOPASSWD: ALL` and can replace
the verifier, unit files, keys, and the protected user. Not secure until
privilege separation is applied by a human and verified from a second session.

### OPTION B — Off-VPS signer + protected local enforcement (recommended)

Operator holds an Ed25519 private key **off this VPS**. The VPS stores only a
public trust identity that is not sufficient to mint approvals. After operator
bootstrap, ubuntu cannot escalate to rewrite the enforcement identity.

**Feasibility now:** protocol scaffolding (`approval-ed25519-v1`) can be built
autonomously. Enforcement and key generation cannot. Status remains
`BLOCKED_SECURITY_BOUNDARY` until bootstrap.

### OPTION C — External approval broker / protected CI environment

GitHub Environments with required reviewers.

**Feasibility now:** insecure. This `gh` token is admin; the repo has no
environments, no branch protection, and no org rule that prevents admin bypass.

## Recommended target

```
AGENT PLANE (ubuntu / Engineering OS)
        │ approval request
        ▼
OPERATOR AUTHORITY PLANE (off-VPS private key)
        │ detached approval-ed25519-v1 signature
        ▼
PROTECTED ACTUATION GATE (hermes-actuator, SO_PEERCRED; ubuntu cannot mutate after H1)
        ▼
hermes-runtime gateway (same-SHA at H1; spawn-transform only at H3)
```

Do not remove sudo, create lockout risk, or apply account changes autonomously.
See `OPERATOR_BOOTSTRAP.md`.
