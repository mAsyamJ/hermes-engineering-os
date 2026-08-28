"""Evaluation engine: eligibility, artifacts, sandbox, comparison, vector."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from engineering_os.evaluation import CONTRACT_VERSION
from engineering_os.evaluation import artifacts as artifact_lib
from engineering_os.evaluation import compare as compare_lib
from engineering_os.evaluation import eligibility as eligibility_lib
from engineering_os.evaluation import llm
from engineering_os.evaluation import policies
from engineering_os.evaluation import profiles as profile_lib
from engineering_os.evaluation import quality
from engineering_os.evaluation import registry
from engineering_os.evaluation import sandbox
from engineering_os.evaluation.artifacts import CaptureResult, tree_hash, DENIED_DIRS

COMMAND_EVALUATORS = {
    "repo.build": "build",
    "repo.tests": "tests",
    "repo.lint": "lint",
    "repo.typecheck": "typecheck",
}


def _identity(**parts: Any) -> str:
    encoded = json.dumps(parts, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _changed_paths(baseline: Path | None, candidate: Path) -> list[str]:
    def files(root: Path) -> set:
        out = set()
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            if any(part in DENIED_DIRS for part in rel.parts):
                continue
            out.add(rel)
        return out

    if baseline is None or not baseline.exists():
        return [str(rel) for rel in sorted(files(candidate))]
    changed = []
    cand_files = files(candidate)
    base_files = files(baseline)
    for rel in sorted(cand_files | base_files):
        left = baseline / rel
        right = candidate / rel
        if not left.exists() or not right.exists() or left.read_bytes() != right.read_bytes():
            changed.append(rel.as_posix())
    return changed


def _command_result(argv: list[str], tree: Path, timeout: int) -> dict[str, Any]:
    ran = sandbox.run_command(argv, tree, timeout_seconds=timeout)
    if ran.timeout or ran.resource_failure or ran.detail in {
        "docker_unavailable",
        "host_timeout",
        "sandbox_runner_failure",
    }:
        verdict = "ERROR"
    elif ran.exit_code == 0:
        verdict = "PASS"
    elif ran.exit_code is None:
        verdict = "ERROR"
    else:
        verdict = "FAIL"
    tests_failed = None
    tests_passed = None
    if "Ran " in (ran.stderr + ran.stdout) or "OK" in (ran.stderr + ran.stdout):
        if ran.exit_code == 0:
            tests_passed = 1
            tests_failed = 0
        else:
            tests_failed = 1
            tests_passed = 0
    return {
        "verdict": verdict,
        "command": argv,
        "exit_code": ran.exit_code,
        "duration_ms": ran.duration_ms,
        "timeout": ran.timeout,
        "resource_failure": ran.resource_failure,
        "stdout": ran.stdout,
        "stderr": ran.stderr,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "sandbox": ran.to_dict(),
    }


def evaluate_trees(
    candidate: Path,
    profile: dict[str, Any],
    baseline: Path | None = None,
    task: dict[str, Any] | None = None,
    github_state: str = "NOT_APPLICABLE",
    eligibility: str = "TEST_ELIGIBLE",
    execution_status: str = "COMPLETE",
) -> dict[str, Any]:
    timeout = int(((profile.get("sandbox") or {}).get("timeout_seconds")) or 60)
    results: dict[str, dict[str, Any]] = {}
    blocked = profile.get("blocked_evaluators") or {}
    if not candidate.exists():
        vector = {name: "UNKNOWN" for name in quality.DIMENSIONS}
        return {
            "contract_version": CONTRACT_VERSION,
            "profile_id": profile.get("profile_id"),
            "profile_version": str(profile.get("profile_version")),
            "profile_hash": profile.get("config_hash"),
            "eligibility": "INSUFFICIENT_EVIDENCE",
            "execution_status": "COMPLETE",
            "results": {},
            "comparisons": {},
            "summary_state": "INSUFFICIENT_EVIDENCE",
            "quality_vector": vector,
            "reason": "missing candidate artifact",
            "candidate_tree_hash": None,
            "baseline_tree_hash": tree_hash(baseline) if baseline and baseline.exists() else None,
        }

    def run_subject(subject: str, tree: Path | None) -> None:
        if tree is None:
            for evaluator_id in COMMAND_EVALUATORS:
                results[f"{evaluator_id}:{subject}"] = {
                    "verdict": "UNKNOWN",
                    "detail": "missing artifact",
                }
            return
        for evaluator_id, key in COMMAND_EVALUATORS.items():
            status = blocked.get(evaluator_id) or blocked.get(key)
            if status:
                results[f"{evaluator_id}:{subject}"] = {"verdict": status, "detail": "profile blocked"}
                continue
            argv = profile_lib.approved_command(profile, key)
            if not argv:
                results[f"{evaluator_id}:{subject}"] = {
                    "verdict": "NOT_APPLICABLE",
                    "detail": f"no {key} command",
                }
                continue
            results[f"{evaluator_id}:{subject}"] = _command_result(argv, tree, timeout)

    run_subject("candidate", candidate)
    run_subject("baseline", baseline)

    comparisons = {}
    for evaluator_id in ("repo.tests", "repo.build", "repo.lint", "repo.typecheck"):
        comparisons[evaluator_id] = compare_lib.classify(
            results.get(f"{evaluator_id}:baseline", {}).get("verdict"),
            results.get(f"{evaluator_id}:candidate", {}).get("verdict"),
        )
    results["repo.regression:candidate"] = {
        "verdict": comparisons.get("repo.tests") or comparisons.get("repo.build") or "UNKNOWN"
    }
    for dim in ("repo.lint", "repo.typecheck"):
        if comparisons.get(dim) == "UNCHANGED_FAILURE":
            results[f"{dim}:candidate"]["verdict"] = "WARN"
            results[f"{dim}:candidate"]["detail"] = "pre-existing violations; none introduced"

    if blocked.get("repo.architecture_policy"):
        results["repo.architecture_policy:candidate"] = {
            "verdict": blocked["repo.architecture_policy"],
            "detail": "profile blocked",
        }
    else:
        results["repo.architecture_policy:candidate"] = policies.architecture_policy(candidate, profile)
    results["repo.scope_policy:candidate"] = policies.scope_policy(
        _changed_paths(baseline, candidate), profile
    )
    results["repo.security:candidate"] = policies.security_policy(candidate, profile)
    results["task.acceptance_checks:candidate"] = policies.acceptance_checks(task)
    results["github.ci:candidate"] = {
        "verdict": github_state if github_state != "AVAILABLE" else "PASS",
        "detail": github_state,
    }
    if github_state == "BLOCKED_AUTH":
        results["github.ci:candidate"]["verdict"] = "BLOCKED_AUTH"
    llm_result = llm.production_judge().evaluate(tree_hash(candidate), "disabled")
    results["llm.judge:candidate"] = {
        "verdict": "NOT_APPLICABLE",
        "experimental": True,
        "disabled": True,
        "detail": llm_result.get("detail"),
    }

    derived = quality.derive_vector(
        results,
        comparisons,
        eligibility=eligibility,
        execution_status=execution_status,
        github_state=github_state,
    )
    return {
        "contract_version": CONTRACT_VERSION,
        "profile_id": profile.get("profile_id"),
        "profile_version": str(profile.get("profile_version")),
        "profile_hash": profile.get("config_hash"),
        "eligibility": eligibility,
        "execution_status": execution_status,
        "results": results,
        "comparisons": comparisons,
        "summary_state": derived["summary_state"],
        "quality_vector": derived["quality_vector"],
        "reason": derived["reason"],
        "candidate_tree_hash": tree_hash(candidate),
        "baseline_tree_hash": tree_hash(baseline) if baseline and baseline.exists() else None,
    }


def evaluate_capture(
    candidate: CaptureResult,
    profile: dict[str, Any],
    baseline: CaptureResult | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    if candidate.secret_scan_status != "PASS" or not candidate.content_hash:
        return {
            "contract_version": CONTRACT_VERSION,
            "eligibility": "INSUFFICIENT_EVIDENCE",
            "execution_status": "COMPLETE",
            "results": {},
            "comparisons": {},
            "summary_state": "INSUFFICIENT_EVIDENCE",
            "quality_vector": {name: "UNKNOWN" for name in quality.DIMENSIONS},
            "reason": candidate.detail or "artifact capture failed guards",
            "candidate_artifact": candidate.to_dict(),
        }
    if candidate.payload:
        actual = hashlib.sha256(candidate.payload).hexdigest()
        if actual != candidate.content_hash:
            return {
                "contract_version": CONTRACT_VERSION,
                "eligibility": "INSUFFICIENT_EVIDENCE",
                "execution_status": "COMPLETE",
                "results": {},
                "comparisons": {},
                "summary_state": "INSUFFICIENT_EVIDENCE",
                "quality_vector": {name: "UNKNOWN" for name in quality.DIMENSIONS},
                "reason": "artifact hash mismatch",
                "candidate_artifact": candidate.to_dict(),
            }
    tmp = Path(tempfile.mkdtemp(prefix="eos-eval-tree-"))
    try:
        cand_dir = tmp / "candidate"
        artifact_lib.materialize_capture(candidate, cand_dir)
        base_dir = None
        if baseline and baseline.secret_scan_status == "PASS" and baseline.payload:
            base_dir = tmp / "baseline"
            artifact_lib.materialize_capture(baseline, base_dir)
        payload = evaluate_trees(cand_dir, profile, baseline=base_dir, **kwargs)
        payload["candidate_artifact"] = candidate.to_dict()
        if baseline:
            payload["baseline_artifact"] = baseline.to_dict()
        return payload
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def identity_hash(payload: dict[str, Any]) -> str:
    return _identity(
        candidate=payload.get("candidate_tree_hash") or payload.get("candidate_artifact", {}).get("content_hash"),
        baseline=payload.get("baseline_tree_hash") or payload.get("baseline_artifact", {}).get("content_hash"),
        profile=payload.get("profile_id"),
        profile_version=payload.get("profile_version"),
        contract=CONTRACT_VERSION,
    )
