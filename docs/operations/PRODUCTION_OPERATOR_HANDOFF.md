# Production Operator Handoff

Work that must happen **outside** autonomous-agent authority.

1. Follow `OPERATOR_BOOTSTRAP.md` to create verified alternate admin access
   before considering any ubuntu sudo reduction.
2. Generate an Ed25519 **private** approval key off this VPS. Never copy it
   onto an ubuntu-readable path.
3. Register only the public trust identity on the protected actuation gate
   after bootstrap.
4. Verify ubuntu cannot replace the verifier, unit, or trust file.
5. Authorize experiment budget in writing if a real MODEL run is desired.
6. Review the canary request package under `.runtime/adaptation/requests/`.
7. Sign Approval A (`approval-ed25519-v1`) only after real evidence and
   production shadow review.
8. Sign Approval B only after a separately authorized bounded canary.

PAR does not perform these actions. Production adaptation remains DISABLED.
