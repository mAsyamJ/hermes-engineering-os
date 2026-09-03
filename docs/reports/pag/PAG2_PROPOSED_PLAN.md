# PAG-2 proposed plan

Not started. Not authorized by PAG-1.

Possible later coverage, in order, only after `docs/reports/pag/PAG2_PREREQUISITES.md`:

1. Secure authority final verification (`scripts/verification/verify-operator-boundary.sh` = PASS)
2. Live Hermes actuation deployment of the pinned upstream transform (separate
   change control; not this VPS' silent apply)
3. Production **read-only** shadow under Approval A semantics
4. Approval A (off-VPS Ed25519, bound hashes, max exposure 1)
5. Signed bounded 1-task canary
6. Automatic safety disable and rollback qualification
7. Approval B
8. Bounded promotion still without auto-promote

Stop lines inherited from PAG-1 remain: no Kanban mutation for routing, no
second scheduler, fail-open Hermes, fail-closed adaptation.
