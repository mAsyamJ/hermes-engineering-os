# Real Hermes Benchmark

Suite: `experiments/benchmarks/real-v1/`  
Evaluator profile: `config/evaluation-profiles/real-v1.yaml`

Disposable Python repositories, not RetroPick. Categories:

- `real-v1-bugfix` — incorrect discount
- `real-v1-feature` — missing multiply
- `real-v1-refactor` — duplicated totals that drifted (broken `right.py`
  omits the last addend so unittest FAIL; golden consolidates `sum`)
- `real-v1-test-repair` — wrong assertion
- `real-v1-config` — timeout 0 vs 30

Each case has `broken/` and `golden/` trees. Phase 4 `quality_vector.tests`
is deterministic. Broken trees FAIL; golden trees PASS. These are not
pre-swapped fixture artifacts used as the experiment conclusion.

No production worktrees. Workspaces are copies under the experiment runtime.
