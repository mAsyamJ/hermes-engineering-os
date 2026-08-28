# Evaluation Profiles

Trusted operator configuration under `config/evaluation-profiles/`.
Task text cannot add shell commands. Commands are argv lists.

| Profile | Version | Status |
|---|---|---|
| fixture | 1 | SUPPORTED Python compile/unittest/lint/typecheck |
| retropick | 1 | BLOCKED_RESOURCE / BLOCKED_ENVIRONMENT (commands recorded from CI, not executed) |
| retropick-android | 1 | BLOCKED_RESOURCE |

Profile version + config hash are part of evaluation identity.
