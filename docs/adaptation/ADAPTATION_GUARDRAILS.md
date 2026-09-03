# Adaptation Guardrails

Deterministic evaluators over Phase 3/4 evidence. No Phoenix raw-span hot
path. No LLM judge.

Each guardrail has metric, threshold or `fail_on`, window, minimum evidence,
and unknown behavior. Critical UNKNOWN blocks promotion. Critical FAIL
auto-disables the candidate for future resolutions. Auto-promotion is
forbidden.
