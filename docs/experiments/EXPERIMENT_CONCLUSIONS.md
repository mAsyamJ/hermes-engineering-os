# Experiment Conclusions

Each persisted result includes effect estimate, uncertainty interval, assigned
N, known N, missing N, assignment integrity, exposure fidelity, analysis
version, reason, and source versions.

| Conclusion | Meaning |
|---|---|
| NOT_STARTED | no assignments |
| COLLECTING | below sample horizon; dashboard may show progress |
| INSUFFICIENT_DATA | horizon reached but coverage/missingness/n too weak |
| INVALIDATED | protocol, contamination, or integrity failed |
| NO_CLEAR_EFFECT | interval includes 0 |
| EVIDENCE_FOR_CANDIDATE | ITT interval excludes 0 toward candidate |
| EVIDENCE_AGAINST_CANDIDATE | ITT interval excludes 0 against candidate |
| GUARDRAIL_FAILURE | safety stop; not an efficacy ranking |

Fixture conclusions are `FIXTURE_VALIDATION_ONLY` and must not enter Phase 5
production intelligence.
