# Evaluation Sandbox

Candidate code is untrusted. Tier C execution uses an ephemeral container
started by Engineering OS. The candidate never receives:

- `/var/run/docker.sock`
- host SSH / Hermes / RetroPick `.env` / observability DB credentials
- unrestricted network

## Image

Reuse already-local `hermes-eos-analytics:phase3`
(`sha256:6a01af80fa2d7147f5857dfe93ac2fd347fb091a6de051d2f5c689e768392702`).
No extra language-image pull in Phase 4 (storage gate).

Controller compose service `evaluation-engine` (profile `evaluate`) may mount
the host Docker CLI + socket. That mount is **not** propagated to the candidate
`docker run`.

## Candidate flags

`--network none --user 65534:65534 --read-only --memory 512m --cpus 1 --pids-limit 128 --cap-drop ALL --security-opt no-new-privileges`

Tmpfs for `/tmp` and `/work`. Artifact copied to `/work`. Timeout 60s default.
Logs truncated to 8 KiB.

## Tiers

- A: metadata/policy in-engine
- B: trusted argv against extracted tree
- C: candidate build/test in the sandbox

Inline sandbox (`EOS_EVAL_SANDBOX=inline`) is for unit tests only.
