"""Fixture canaries A/B/C. No Hermes worker, no RetroPick mutation, no LLM spend."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from engineering_os.analytics.db import connect
from engineering_os.evaluation.engine import evaluate_trees
from engineering_os.evaluation.persist import persist_run
from engineering_os.evaluation.profiles import load_profile


def run() -> dict:
    src = Path(__file__).resolve().parents[2] / "tests/evaluation/fixture_src"
    profile = load_profile("fixture")
    work = Path(tempfile.mkdtemp(prefix="eos-canary-"))
    clean = work / "clean"
    broken = work / "broken"
    shutil.copytree(src, clean)
    shutil.copytree(src, broken)
    (broken / "src/app.py").write_text("def add(left, right):\n    return left - right\n")
    cases = [
        ("t_eval_canary_a", clean, clean),
        ("t_eval_canary_b", broken, clean),
        ("t_eval_canary_c", clean, broken),
    ]
    expected = {
        "t_eval_canary_a": "UNCHANGED_PASS",
        "t_eval_canary_b": "INTRODUCED_FAILURE",
        "t_eval_canary_c": "FIXED_FAILURE",
    }
    out = []
    with connect() as connection:
        for task_id, cand, base in cases:
            payload = evaluate_trees(
                cand, profile, baseline=base, eligibility="TEST_ELIGIBLE", github_state="NOT_APPLICABLE"
            )
            got = payload["comparisons"]["repo.tests"]
            if got != expected[task_id]:
                raise SystemExit(f"{task_id} expected {expected[task_id]} got {got}")
            persisted = persist_run(
                connection,
                payload,
                {
                    "board": "eos-phase4-eval",
                    "task_id": task_id,
                    "cohort": "fixture",
                    "recompute": True,
                    "trace_id": "3c6a188a33999ef09cf0bc74c2cae76b" if task_id == "t_eval_canary_a" else None,
                },
            )
            projection = None
            if task_id == "t_eval_canary_a":
                from engineering_os.evaluation.persist import persist_projection
                from engineering_os.evaluation.project import project_vector

                projection = project_vector(
                    "3c6a188a33999ef09cf0bc74c2cae76b",
                    persisted["evaluation_run_id"],
                    payload["quality_vector"],
                )
                persist_projection(connection, persisted["evaluation_run_id"], projection)
            connection.commit()
            out.append({"task_id": task_id, "comparison": got, "projection": projection, **persisted})
    shutil.rmtree(work, ignore_errors=True)
    return {"status": "success", "canaries": out}


def main() -> int:
    print(json.dumps(run(), default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
