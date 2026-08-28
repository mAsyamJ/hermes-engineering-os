"""Phoenix CODE annotation projection. Secondary; fail-open."""

from __future__ import annotations

import urllib.error
from typing import Any

from engineering_os.observability import phoenix_client

ANNOTATION_NAMES = (
    "evaluation.correctness",
    "evaluation.tests",
    "evaluation.regression",
    "evaluation.build",
)


def project_vector(
    trace_id: str,
    evaluation_run_id: str,
    vector: dict[str, Any],
    identifier_prefix: str = "phase4-eval-v1",
) -> dict[str, Any]:
    if not trace_id:
        return {"status": "PENDING", "detail": "no correlated trace"}
    inputs = []
    for name in ANNOTATION_NAMES:
        dim = name.split(".", 1)[1]
        label = vector.get(dim)
        if not label:
            continue
        inputs.append(
            {
                "traceId": trace_id,
                "name": name,
                "annotatorKind": "CODE",
                "label": str(label),
                "explanation": f"canonical evaluation_run_id={evaluation_run_id}",
                "metadata": {
                    "canonical_store": "hermes_engineering",
                    "evaluation_run_id": evaluation_run_id,
                    "contract": "phase4-eval-v1",
                    "projection": True,
                },
                "source": "API",
                "identifier": f"{identifier_prefix}:{evaluation_run_id}:{name}",
            }
        )
    if not inputs:
        return {"status": "PENDING", "detail": "no projectable dimensions"}
    try:
        phoenix_client.graphql(
            """
            mutation ProjectEval($input: [CreateTraceAnnotationInput!]!) {
              createTraceAnnotations(input: $input) {
                traceAnnotations { id name label identifier }
              }
            }
            """,
            {"input": inputs},
        )
        return {"status": "PROJECTED", "count": len(inputs), "canonical": False}
    except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as exc:
        return {
            "status": "DEGRADED",
            "detail": f"{type(exc).__name__}: {exc}",
            "canonical": False,
        }
