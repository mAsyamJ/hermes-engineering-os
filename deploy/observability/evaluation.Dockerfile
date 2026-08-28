# Candidate sandbox. Reuse the already-local analytics image; do not pull latest.
# Inspected 2026-08-27: sha256:6a01af80fa2d7147f5857dfe93ac2fd347fb091a6de051d2f5c689e768392702
# Storage gate: never pull Node/Go/Playwright/Android images in Phase 4.
FROM hermes-eos-analytics:phase3
WORKDIR /work
ENV HOME=/tmp
ENV LANG=C
ENV PYTHONDONTWRITEBYTECODE=1
USER 65534:65534
