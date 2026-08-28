# Adaptation Rollback

Every active candidate policy has a predefined last-known-good fallback hash.

## Behavior

- Stop assigning **new** candidate tasks / fixture units.
- Restore resolver binding to baseline (or the named fallback bundle).
- Atomic via CAS on `adaptation_bindings.binding_version`.
- Idempotent: a second rollback of an already-rolled-back binding is success
  with `already_baseline`.
- Future-only. Running tasks are not killed or rewritten.
- Git is not reset. Evidence and audit rows are not deleted.

## Health check after rollback

Resolver returns baseline. Zero new candidate exposures. Hermes and
dispatcher remain healthy. Prior candidate exposures stay auditable.
Metrics continue collecting.

## Auto-disable vs auto-promotion

Critical guardrail FAIL may **automatically disable** the candidate for
future resolutions (reduce blast radius). The system must not automatically
**increase** blast radius. Promotion always requires Approval B.
