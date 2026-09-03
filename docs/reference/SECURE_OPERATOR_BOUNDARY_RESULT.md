# Secure Operator Boundary Result

Command: `scripts/verification/verify-operator-boundary.sh`

**Result: READY_FOR_HUMAN** (2026-08-29 16:51Z re-verified). This is not PASS.

Live principals: `ubuntu:1000` plus `hermes-op:1001` (SSH public key
installed; sudoers-hermes-op installed). Gateways still run as ubuntu.
No `/etc/hermes-eos`, no `hermes-runtime` / `hermes-actuator`.
`scripts/deployment/h1-postcheck.sh` exits 1 (`H1 POSTCHECK: NOT PASS`).

H1 procedure: `docs/reference/OPERATOR_BOOTSTRAP.md` and
`.runtime/operator-bootstrap/`. Baseline capture:
`.runtime/h1-baseline/before-20260829T154257Z.txt`.

This document will be rewritten to PASS only after the verifier prints
`status=PASS` on this machine.
