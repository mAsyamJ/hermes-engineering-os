# Upgrade Policy

No dependency or upstream pin is upgraded blindly.

1. Review upstream changelog, license, repository state, and Hermes SDK/API
   compatibility.
2. Update one exact commit in `provenance/UPSTREAM_LOCK.yaml`.
3. Re-clone with `scripts/clone-upstreams.sh`.
4. Re-audit every copied or modified path and update notices/vendor map.
5. Rebuild tracked dashboard output.
6. Run isolated plugin and browser qualification.
7. Capture production boundaries and owner-only plugin backup.
8. Install/rescan; restart only the dashboard if backend mounting changed.
9. Run `scripts/verify.sh`.

Do not upgrade Hermes source or its virtual environment from this repository.
The existing Hermes checkout has preserved source drift and remains a separate
operator-owned system.

OTel repair in Phase 2 must compare the installed plugin to pinned upstream,
snapshot the active Python environment again, and preserve fail-open behavior.
Future analytics should use one dedicated Hermes Engineering PostgreSQL
server/container with isolated databases and roles; never reuse RetroPick
databases.

