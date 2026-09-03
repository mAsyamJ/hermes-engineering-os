# Performance Data Quality

Verifier: `scripts/verification/verify-performance-data.sh`.

Invalid if:

- known_n > population_n
- quality metric treats INSUFFICIENT_EVIDENCE as FAIL
- fixture/canary identity appears in a production aggregate dimension
- SINGLE_MODEL slice contains MIXED_MODEL
- profile or prompt version claimed without evidence
- NOT_COMPARABLE row carries a numeric effect
- INSUFFICIENT_DATA presented as SUPPORTED
- coverage metadata missing when population_n>0 and known_n>0
- incompatible ruleset/contract marked COMPARABLE
- unknown rows silently dropped from population_n
