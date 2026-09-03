# Adaptation Audit

`adaptation_audit_log` is append-only (trigger rejects UPDATE/DELETE).

Events include: recommendation, approval request, approve-test, compile-policy,
shadow-start, canary-start-fixture, disable, rollback, promotion-request,
bind, disable-all.

Fields: event id, time, actor class/identity, action, object, previous/new
state hashes, reason, source evidence. Secrets and approval signatures are
not written to the dashboard API. Signatures stored in `adaptation_approvals`
are not selected by `/adaptation/audit`.
