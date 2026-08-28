"""Deterministic evaluation eligibility. Missing artifacts are not failures."""

from __future__ import annotations

from typing import Any

from engineering_os.evaluation.profiles import load_profile


def classify_task(
    task: dict[str, Any] | None,
    git: dict[str, Any] | None = None,
    cohort: str = "production",
    profile_id: str | None = None,
) -> dict[str, str]:
    if task is None:
        return {
            "eligibility": "INSUFFICIENT_EVIDENCE",
            "reason": "task row is missing",
        }
    if cohort == "excluded":
        return {"eligibility": "EXCLUDED", "reason": "task is out of evaluation scope"}
    git = git or {}
    sha = git.get("commit_sha")
    quality = str(git.get("evidence_quality") or git.get("git_evidence_state") or "")
    repository = git.get("repository_id") or task.get("repository_id")
    if profile_id:
        try:
            profile = load_profile(profile_id)
        except FileNotFoundError:
            return {
                "eligibility": "NOT_APPLICABLE",
                "reason": f"no evaluation profile for {profile_id}",
            }
        if profile.get("status") in {"BLOCKED_RESOURCE", "UNSUPPORTED"}:
            return {
                "eligibility": "NOT_APPLICABLE",
                "reason": f"profile {profile_id} is {profile.get('status')}",
            }
    if cohort == "fixture":
        if sha or task.get("artifact_hash"):
            return {
                "eligibility": "TEST_ELIGIBLE",
                "reason": "fixture cohort with reproducible artifact identity",
            }
        if task.get("workspace_path") and str(task.get("workspace_path")).startswith(
            "/opt/hermes-engineering-os/.runtime/"
        ):
            return {
                "eligibility": "TEST_ELIGIBLE",
                "reason": "fixture workspace under Engineering OS runtime",
            }
        return {
            "eligibility": "INSUFFICIENT_EVIDENCE",
            "reason": "fixture task has no captured artifact yet",
        }
    if quality == "AVAILABLE" and sha:
        return {
            "eligibility": "ELIGIBLE",
            "reason": "exact candidate commit SHA is recorded",
        }
    if task.get("artifact_hash"):
        return {
            "eligibility": "ELIGIBLE",
            "reason": "immutable candidate artifact hash is already stored",
        }
    return {
        "eligibility": "INSUFFICIENT_EVIDENCE",
        "reason": "no immutable candidate commit or content-hashed artifact; current workspace bytes are not a historical run",
    }


def profile_for_repository(repository_id: str | None) -> str | None:
    mapping = {
        "fixture": "fixture",
        "retropick": "retropick",
        "retropick-android": "retropick-android",
    }
    if not repository_id:
        return None
    return mapping.get(repository_id)
