# Performance Statistics

Standard library only. No SciPy/NumPy.

Binary rates use a Wilson score interval with z=1.96. Wilson is defined at
0/n and n/n and has better small-sample coverage than Wald.

Difference of proportions uses right−left with a conservative combination of
the two Wilson intervals. Relative difference is undefined when the left
estimate is 0.

Continuous measures: n, median, p25, p75, IQR, supplemental mean. p90/p95
only when sample size meets the tier config. Outliers must not own the median.

n=0 returns null estimates and NO_DATA, never a fabricated 0%.
