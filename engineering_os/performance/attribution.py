"""Observational attribution. Never infers causality. Never NLP-classifies titles."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


def model_identity(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("provider") or ""),
        str(row.get("model") or ""),
        str(row.get("source") or ""),
    )


def model_key(provider: str, model: str) -> str:
    if provider:
        return f"{provider}/{model}"
    return model or "UNKNOWN"


def classify_model_attribution(usage_rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(usage_rows)
    if not rows:
        return {
            "attribution": "UNKNOWN",
            "identities": [],
            "provider_model_keys": [],
        }
    identities = sorted({model_identity(row) for row in rows})
    provider_models = sorted({(provider, model) for provider, model, _source in identities})
    if len(provider_models) == 1:
        attribution = "SINGLE_MODEL"
    else:
        attribution = "MIXED_MODEL"
    return {
        "attribution": attribution,
        "identities": [
            {"provider": p, "model": m, "source": s}
            for p, m, s in identities
        ],
        "provider_model_keys": [model_key(p, m) for p, m in provider_models],
    }


def classify_skill_attribution(usage_rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(usage_rows)
    names = sorted({str(row.get("skill_name") or "") for row in rows if row.get("skill_name")})
    if not names:
        attribution = "NO_SKILL"
    elif len(names) == 1:
        attribution = "SINGLE_SKILL"
    else:
        attribution = "MULTI_SKILL"
    return {
        "attribution": attribution,
        "skills": [
            {
                "skill_name": name,
                "version": None,
                "source": next(
                    (str(row.get("source") or "") for row in rows if row.get("skill_name") == name),
                    "",
                ),
            }
            for name in names
        ],
    }


def profile_identity(task: dict[str, Any]) -> dict[str, Any]:
    name = task.get("profile")
    return {
        "profile_name": str(name) if name else None,
        "profile_config_version": None,
        "profile_config_version_coverage": "UNKNOWN",
        "label": "profile name, not immutable configuration version",
    }


def prompt_version_status() -> dict[str, str]:
    return {
        "prompt_version_performance": "UNSUPPORTED_EVIDENCE",
        "reason": "no immutable prompt/config/system-prompt hash was recorded at execution time",
    }


def attach_attribution(
    tasks: list[dict[str, Any]],
    model_rows: list[dict[str, Any]],
    skill_rows: list[dict[str, Any]],
    run_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    runs_by_task: dict[tuple[str, str], list[int]] = defaultdict(list)
    for run in run_rows:
        if run.get("qualifying"):
            runs_by_task[(str(run["board"]), str(run["task_id"]))].append(int(run["run_id"]))
    models_by_run: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in model_rows:
        models_by_run[(str(row["board"]), int(row["run_id"]))].append(row)
    skills_by_run: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in skill_rows:
        skills_by_run[(str(row["board"]), int(row["run_id"]))].append(row)

    enriched: list[dict[str, Any]] = []
    for task in tasks:
        key = (str(task["board"]), str(task["task_id"]))
        run_ids = runs_by_task.get(key, [])
        model_usage = []
        skill_usage = []
        for run_id in run_ids:
            model_usage.extend(models_by_run.get((key[0], run_id), []))
            skill_usage.extend(skills_by_run.get((key[0], run_id), []))
        models = classify_model_attribution(model_usage)
        skills = classify_skill_attribution(skill_usage)
        profile = profile_identity(task)
        item = dict(task)
        item["model_attribution"] = models["attribution"]
        item["model_identities"] = models["identities"]
        item["model_keys"] = models["provider_model_keys"]
        item["skill_attribution"] = skills["attribution"]
        item["skills"] = skills["skills"]
        item["profile_name"] = profile["profile_name"]
        item["profile_config_version"] = None
        item["prompt_version"] = None
        enriched.append(item)
    return enriched
