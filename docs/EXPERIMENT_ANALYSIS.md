# Experiment Analysis (`phase6-analysis-v1`)

Primary analysis is INTENTION_TO_TREAT using assigned arms.

Independent binary: difference of proportions with Wilson z=1.96 combination
from `engineering_os.performance.stats`. Paired binary: discordance table
plus the same Wilson difference on complete pairs (`paired-binary-wilson-v1`).
Continuous plans require operator-supplied variance; none is invented.

No p-value optimization. No hidden metric search. Secondary metrics are
exploratory. Guardrails are safety, not efficacy.

Fixed horizon: confirmatory `EVIDENCE_*` is blocked (`BLOCKED_HORIZON`) until
planned N is collected. Safety guardrail stop may pause collection without
declaring the candidate statistically worse.

Stdlib `math` only. No SciPy/NumPy.
