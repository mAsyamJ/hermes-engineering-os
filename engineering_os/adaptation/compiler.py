"""Compile a validated recommendation + operator YAML into an immutable bundle."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engineering_os.adaptation.recommend import recommend_from_result
from engineering_os.adaptation.schema import PolicyError, load_id, load_path, validate_raw
from engineering_os.experiments.config_snapshot import canonical_dumps, sha256_text, variant_snapshot


class CompileError(PolicyError):
    pass


def compile_policy(
    recommendation: dict[str, Any],
    policy: dict[str, Any] | str | Path,
) -> dict[str, Any]:
    if recommendation.get("classification") == "NOT_PROMOTABLE":
        raise CompileError("cannot compile a NOT_PROMOTABLE recommendation")
    if recommendation.get("state") == "NOT_PROMOTABLE":
        raise CompileError("cannot compile a NOT_PROMOTABLE recommendation")
    if isinstance(policy, (str, Path)):
        path = Path(policy)
        spec = load_path(path) if path.suffix in {".yaml", ".yml"} else load_id(str(policy))
    else:
        spec = validate_raw(dict(policy))
    source = recommendation.get("source_result") or {}
    rec_experiment = source.get("experiment_id") or recommendation.get("experiment_id")
    if spec.get("source_experiment") and rec_experiment and spec["source_experiment"] != rec_experiment:
        raise CompileError("policy source_experiment does not match recommendation")
    rec_treatment = source.get("treatment_dimension") or recommendation.get("treatment_dimension")
    if rec_treatment and spec["treatment_dimension"] != rec_treatment:
        raise CompileError("treatment_dimension mismatch")
    rec_scope = source.get("scope") or recommendation.get("scope")
    if rec_scope == "FIXTURE" and spec["scope"] in {
        "PRODUCTION_CANARY",
        "PRODUCTION_BOUNDED",
        "PRODUCTION_FULL",
    }:
        raise CompileError("fixture evidence cannot compile a production actuation policy")
    if recommendation.get("classification") == "TEST_ONLY" and spec["scope"] in {
        "PRODUCTION_CANARY",
        "PRODUCTION_BOUNDED",
        "PRODUCTION_FULL",
    }:
        raise CompileError("TEST_ONLY recommendation cannot compile production actuation policy")
    candidate = spec["candidate"]
    fallback = spec["fallback"]
    if not candidate.get("config_hash"):
        snap = variant_snapshot(
            variant_id=candidate["variant_id"],
            variant_name=candidate.get("variant_name") or candidate["variant_id"],
            treatment_dimension=spec["treatment_dimension"],
            artifact={"name": candidate.get("artifact") or "clean"},
        )
        candidate = {**candidate, "config_hash": snap["config_hash"], "snapshot": snap["snapshot"]}
        spec["candidate"] = candidate
    if not fallback.get("config_hash"):
        snap = variant_snapshot(
            variant_id=fallback["variant_id"],
            variant_name=fallback.get("variant_name") or fallback["variant_id"],
            treatment_dimension=spec["treatment_dimension"],
            artifact={"name": fallback.get("artifact") or "clean"},
        )
        fallback = {**fallback, "config_hash": snap["config_hash"], "snapshot": snap["snapshot"]}
        spec["fallback"] = fallback
    if spec["rollback"].get("target") not in {fallback.get("config_hash"), "baseline", fallback.get("variant_id")}:
        if spec["rollback"]["target"] not in {"fallback", "BASELINE", "baseline-hermes"}:
            # allow explicit fallback variant id or hash; otherwise require fallback
            if spec["rollback"]["target"] != fallback["variant_id"]:
                raise CompileError("rollback.target must name the fallback variant, hash, or baseline")
    spec["rollback"]["fallback_config_hash"] = fallback["config_hash"]
    spec["source_recommendation_hash"] = recommendation.get("recommendation_hash")
    spec["source_classification"] = recommendation.get("classification")
    body = {k: v for k, v in spec.items() if not str(k).startswith("_")}
    policy_hash = sha256_text(canonical_dumps(body))
    spec["_policy_hash"] = policy_hash
    return {
        "status": "success",
        "policy_id": spec["policy_id"],
        "policy_version": spec["policy_version"],
        "policy_hash": policy_hash,
        "scope": spec["scope"],
        "treatment_dimension": spec["treatment_dimension"],
        "candidate_config_hash": candidate["config_hash"],
        "fallback_config_hash": fallback["config_hash"],
        "classification": recommendation.get("classification"),
        "immutable": True,
        "spec": spec,
        "auto_promote": False,
    }


def hash_bundle(spec: dict[str, Any]) -> str:
    body = {k: v for k, v in spec.items() if not str(k).startswith("_")}
    return sha256_text(canonical_dumps(body))
