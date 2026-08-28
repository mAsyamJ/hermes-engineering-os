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

Phase 2 OTel packages are pinned in `requirements/hermes-otel.constraints.txt`
(OpenTelemetry 1.44.0, compatible with production `protobuf==7.35.1`). Do not
install hermes-otel lockfile 1.41.0 into the Hermes venv.

Future evaluation must keep using the dedicated `hermes_engineering` database on
the observability Postgres; never reuse RetroPick databases. Do not upgrade
Phoenix merely to add evaluation features. Do not pull unbounded evaluation
images; keep root free ≥20 GiB.

