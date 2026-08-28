# Experiment Benchmarks

Trusted suites live in `experiments/benchmarks/`. V1 uses `fixture-v1` copied
from `tests/evaluation/fixture_src`. Cases are `clean` (add returns sum) or
`broken` (add returns difference). Evaluation uses Phase 4 profile `fixture`
and `quality_vector.tests` as the primary metric.

Workspaces are disposable copies under `$EOS_EXPERIMENT_RUNTIME` or `/tmp`.
Never `/opt/retropick`. Cross-arm trees must not share paths.

Repeated identical fixtures qualify the platform. They do not prove general
production causal effects. Scope is `FIXTURE`; results are
`FIXTURE_VALIDATION_ONLY`.
