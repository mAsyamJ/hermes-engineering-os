# Secure Operator Boundary Result

Command: `scripts/verify-operator-boundary.sh`

**Result: READY_FOR_HUMAN** (2026-08-29). This is not PASS.

Live principals: `ubuntu:1000` only. Gateways run as ubuntu
(PIDs 2381797 default, 924 rp-friend). No `/etc/hermes-eos`, no
`hermes-op` / `hermes-runtime` / `hermes-actuator`.

H1 procedure: `docs/OPERATOR_BOOTSTRAP.md` and
`.runtime/operator-bootstrap/`. Baseline capture:
`.runtime/h1-baseline/before-20260829T120653Z.txt`.

This document will be rewritten to PASS only after the verifier prints
`status=PASS` on this machine.
