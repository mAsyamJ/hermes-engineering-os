"""Disabled LLM evaluator interface. No production judging. No API spend."""

from __future__ import annotations

from typing import Any, Protocol


class LLMEvaluator(Protocol):
    def evaluate(self, artifact_hash: str, prompt: str) -> dict[str, Any]:
        ...


class DisabledLLMEvaluator:
    enabled = False
    experimental = True

    def evaluate(self, artifact_hash: str, prompt: str) -> dict[str, Any]:
        return {
            "verdict": "NOT_APPLICABLE",
            "disabled": True,
            "experimental": True,
            "detail": "llm.judge is DISABLED in phase4-eval-v1",
            "artifact_hash": artifact_hash,
        }


class FakeLLMEvaluator:
    enabled = False
    experimental = True

    def __init__(self, canned: dict[str, Any] | None = None) -> None:
        self.canned = canned or {"verdict": "UNKNOWN", "detail": "fake"}

    def evaluate(self, artifact_hash: str, prompt: str) -> dict[str, Any]:
        return {
            **self.canned,
            "experimental": True,
            "disabled": True,
            "artifact_hash": artifact_hash,
            "canonical": False,
        }


def production_judge() -> LLMEvaluator:
    return DisabledLLMEvaluator()
