# Adaptation Validity

A candidate policy is usable only when all of the following hold:

- source recommendation exists and is not `NOT_PROMOTABLE`
- source experiment not `INVALIDATED`
- policy hash matches Git + stored bundle
- approval exists, unexpired, hash-bound, scope-bound, class-compatible
- TEST approval is not used for PRODUCTION_* 
- fallback config hash present
- guardrails defined
- rollback target defined
- no POLICY_CONFLICT at the matched precedence
- kill switch not engaged
- required Phase 3/4 evidence known when promoting
- no config / contract / approval drift

Critical guardrail UNKNOWN → no further promotion.
Critical guardrail FAIL → auto-disable.
Missing Phase 3 or Phase 4 → freeze promotion (candidate not expanded).

Production policy additionally requires a secure human boundary, real Phase 6
causal evidence, supported runtime actuation, and memory isolation where the
treatment needs it. Those are currently BLOCKED; validity must not paper over
them.
