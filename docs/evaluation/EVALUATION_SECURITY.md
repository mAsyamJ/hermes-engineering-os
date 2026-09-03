# Evaluation Security

- Candidate network disabled by default
- No Docker socket in the candidate
- No host SSH, Hermes secrets, RetroPick `.env`, or DB passwords in candidate env
- Secret scan on artifacts; `FAKE_PHASE4_SECRET_ABC123` must not leak into DB/API/UI/logs
- Plugin APIs remain GET-only
- Postgres unpublished
- LLM judge disabled; no evaluation API spend

Report a leak with the same Engineering OS uninstall path as SECURITY.md.
