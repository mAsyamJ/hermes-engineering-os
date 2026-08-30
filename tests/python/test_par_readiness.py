"""PAR / par-v1 qualification. Honest blockers stay blocked."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("EOS_EVAL_SANDBOX", "inline")
os.environ["EOS_ADAPTATION_RUNTIME"] = tempfile.mkdtemp(prefix="eos-par-adapt-")
os.environ["EOS_EXPERIMENT_RUNTIME"] = tempfile.mkdtemp(prefix="eos-par-exp-")

from engineering_os.adaptation.approval import approve_production, sign_test, verify_test
from engineering_os.adaptation.approval_ed25519 import (
    APPROVAL_ED25519_ALG,
    generate_approval_request,
    generate_ephemeral_keypair,
    sign_detached,
    verify_bindings,
    verify_detached_signature,
    verify_production_authorization,
    verify_scope_class,
)
from engineering_os.adaptation.canary_package import generate_package
from engineering_os.adaptation.readiness import cell, cells
from engineering_os.adaptation.recommend import recommend_from_result
from engineering_os.adaptation.spawn_resolve import resolve_spawn_configuration
from engineering_os.experiments.benchmarks import materialize_real_case
from engineering_os.experiments.budget_gate import require_budget_authorization
from engineering_os.experiments.definitions import load_id
from engineering_os.experiments.exposure_identity import identity_graph
from engineering_os.experiments.hermes_runner import run_real_unit
from engineering_os.experiments.memory_snapshot import (
    create_isolated_arms,
    destroy_homes,
    freeze_snapshot,
    memory_hash,
    production_memory_fingerprint,
    write_memory,
)
from engineering_os.evaluation.engine import evaluate_trees
from engineering_os.evaluation.profiles import load_profile


ROOT = Path(__file__).resolve().parents[2]
FAKE_SECRET = "FAKE_PAR_SECRET_ABC123"


def _request(**overrides):
    payload = generate_approval_request(
        recommendation_id="rec-1",
        policy_id="policy-1",
        policy_hash="phash",
        policy_version="1",
        approval_stage="A",
        scope="BENCHMARK",
        maximum_exposure=1,
        candidate_config_hash="cand",
        fallback_hash="fall",
        rollback_hash="roll",
        expiry="2027-01-01T00:00:00+00:00",
    )
    payload.update(overrides)
    return payload


class ApprovalProtocolTests(unittest.TestCase):
    def test_ed25519_roundtrip_and_mismatches(self) -> None:
        keys = generate_ephemeral_keypair()
        request = _request()
        sig = sign_detached(request, keys["private"])
        self.assertTrue(verify_detached_signature(request, sig, keys["public"], consume=False)["ok"])
        self.assertFalse(
            verify_detached_signature({**request, "policy_hash": "other"}, sig, keys["public"], consume=False)["ok"]
        )
        self.assertFalse(
            verify_detached_signature({**request, "scope": "PRODUCTION_CANARY"}, sig, keys["public"], consume=False)["ok"]
        )
        expired = {**request, "expiry": "2020-01-01T00:00:00+00:00"}
        self.assertEqual(
            verify_detached_signature(expired, sign_detached(expired, keys["private"]), keys["public"], consume=False)["reason"],
            "approval expired",
        )
        other = generate_ephemeral_keypair()
        self.assertEqual(
            verify_detached_signature(request, sig, other["public"], consume=False)["reason"],
            "signature mismatch",
        )
        first = verify_detached_signature(request, sig, keys["public"], consume=True)
        self.assertTrue(first["ok"])
        self.assertEqual(verify_detached_signature(request, sig, keys["public"], consume=True)["reason"], "replay")

    def test_modified_rollback_and_exposure_rejected(self) -> None:
        request = _request()
        expected = {
            "policy_hash": request["policy_hash"],
            "scope": request["scope"],
            "approval_stage": request["approval_stage"],
            "recommendation_id": request["recommendation_id"],
            "candidate_config_hash": request["candidate_config_hash"],
            "rollback_hash": request["rollback_hash"],
            "maximum_exposure": request["maximum_exposure"],
        }
        self.assertTrue(verify_bindings(request, expected)["ok"])
        self.assertFalse(verify_bindings({**request, "rollback_hash": "x"}, expected)["ok"])
        self.assertFalse(verify_bindings({**request, "maximum_exposure": "99"}, expected)["ok"])
        self.assertFalse(verify_bindings({**request, "candidate_config_hash": "x"}, expected)["ok"])

    def test_cross_class_rejection(self) -> None:
        self.assertFalse(verify_scope_class(scope="PRODUCTION_CANARY", approval_class="TEST")["ok"])
        self.assertFalse(verify_scope_class(scope="FIXTURE", approval_class="PRODUCTION")["ok"])
        hmac_fields = {
            "stage": "A",
            "recommendation_id": "r",
            "policy_hash": "h",
            "policy_version": "1",
            "scope": "FIXTURE",
            "max_exposure": 1,
            "expires_at": "2027-01-01T00:00:00+00:00",
            "rollback_hash": "rb",
            "operator_identity": "tester",
        }
        hmac_sig = sign_test(hmac_fields, key=b"test-key")
        self.assertTrue(verify_test(hmac_fields, hmac_sig, key=b"test-key")["ok"])
        request = _request(algorithm="approve-hmac-sha256-v1-test")
        keys = generate_ephemeral_keypair()
        self.assertFalse(verify_detached_signature(request, hmac_sig, keys["public"], consume=False)["ok"])

    def test_production_verify_blocked(self) -> None:
        payload = verify_production_authorization()
        self.assertIn(payload["status"], {"BLOCKED_SECURITY_BOUNDARY", "PROTECTED_TRUST_PRESENT"})
        self.assertFalse(payload["granted"])
        blocked = approve_production()
        self.assertEqual(blocked["status"], "BLOCKED_APPROVAL_BOUNDARY")


class SpawnResolverTests(unittest.TestCase):
    def test_production_disabled(self) -> None:
        result = resolve_spawn_configuration(
            {"scope": "PRODUCTION_CANARY", "environment": "production"},
            {"model": "gpt-5.6-sol"},
        )
        self.assertEqual(result["resolution"], "BASELINE")
        self.assertFalse(result["actuate"])
        self.assertEqual(result["effective"]["model"], "gpt-5.6-sol")

    def test_exception_and_conflict_baseline(self) -> None:
        result = resolve_spawn_configuration({"board": "x"}, {"model": "base"}, state={"bindings": "bad"})
        self.assertEqual(result["resolution"], "BASELINE")
        spec = {
            "policy_id": "p",
            "selectors": {"match": "ALL", "conditions": [{"field": "board", "op": "EQ", "values": ["b"]}]},
            "candidate": {"overrides": {"model": "cand"}},
        }
        state = {
            "kill_switch": False,
            "bindings": [
                {"policy_id": "a", "state": "ACTIVE", "mode": "CANARY", "spec": spec, "selectors": spec["selectors"]},
                {"policy_id": "b", "state": "ACTIVE", "mode": "CANARY", "spec": spec, "selectors": spec["selectors"]},
            ],
        }
        conflict = resolve_spawn_configuration({"board": "b"}, {"model": "base"}, state=state)
        self.assertEqual(conflict["resolution"], "BASELINE")

    def test_approved_non_production_override(self) -> None:
        spec = {
            "policy_id": "p",
            "_policy_hash": "h",
            "candidate_config_hash": "cand",
            "fallback_config_hash": "fall",
            "selectors": {"match": "ALL", "conditions": [{"field": "board", "op": "EQ", "values": ["eos"]}]},
            "candidate": {"overrides": {"model": "gpt-5.6-terra", "provider": "openai-codex"}},
        }
        state = {
            "kill_switch": False,
            "bindings": [{"policy_id": "p", "state": "ACTIVE", "mode": "CANARY", "spec": spec, "selectors": spec["selectors"]}],
        }
        result = resolve_spawn_configuration(
            {"board": "eos", "scope": "BENCHMARK", "environment": "benchmark"},
            {"model": "gpt-5.6-sol", "provider": "openai-codex"},
            state=state,
        )
        self.assertEqual(result["resolution"], "CANDIDATE")
        self.assertEqual(result["effective"]["model"], "gpt-5.6-terra")
        self.assertFalse(result["mutated_kanban"])


class MemoryIsolationTests(unittest.TestCase):
    def test_cross_arm_and_secret_free(self) -> None:
        before = production_memory_fingerprint()
        snapshot = freeze_snapshot(memory_text="start", user_text="user", config={"model": "x", "api_key": FAKE_SECRET})
        self.assertNotIn(FAKE_SECRET, snapshot["canonical"])
        arms = create_isolated_arms(snapshot, prefix="par8")
        self.assertTrue(arms["identical_initial_hash"])
        root = Path(arms["root"])
        write_memory(Path(arms["arm_a"]["path"]), "arm-a-write")
        self.assertNotEqual(memory_hash(Path(arms["arm_a"]["path"])), memory_hash(Path(arms["arm_b"]["path"])))
        write_memory(Path(arms["arm_b"]["path"]), "arm-b-write")
        self.assertNotEqual(memory_hash(Path(arms["arm_a"]["path"])), memory_hash(Path(arms["arm_b"]["path"])))
        self.assertEqual(production_memory_fingerprint(), before)
        destroy_homes(root)
        self.assertFalse(root.exists())
        self.assertEqual(production_memory_fingerprint(), before)


class ExperimentReadinessTests(unittest.TestCase):
    def test_real_protocol_is_prepared_not_executed(self) -> None:
        definition = load_id("real-model-sol-vs-terra-v1")
        self.assertEqual(definition["treatment_dimension"], "MODEL")
        self.assertEqual(definition["_execution"], "PREPARED")
        self.assertEqual(int(definition["budget"]["max_llm_calls"]), 0)
        gate = require_budget_authorization()
        self.assertFalse(gate["ok"])
        blocked = run_real_unit({}, definition)
        self.assertFalse(blocked["executed"])

    def test_real_benchmark_evaluator(self) -> None:
        work = Path(os.environ["EOS_EXPERIMENT_RUNTIME"]) / "real-eval"
        profile = load_profile("real-v1")
        for case_id in ("real-v1-bugfix", "real-v1-feature", "real-v1-refactor", "real-v1-test-repair", "real-v1-config"):
            broken = materialize_real_case({"case_id": case_id, "tree": "broken"}, work / f"{case_id}-broken")
            golden = materialize_real_case({"case_id": case_id, "tree": "golden"}, work / f"{case_id}-golden")
            broken_eval = evaluate_trees(Path(broken["path"]), profile, baseline=Path(broken["path"]), eligibility="TEST_ELIGIBLE")
            golden_eval = evaluate_trees(Path(golden["path"]), profile, baseline=Path(golden["path"]), eligibility="TEST_ELIGIBLE")
            self.assertEqual(broken_eval["quality_vector"]["tests"], "FAIL", case_id)
            self.assertEqual(golden_eval["quality_vector"]["tests"], "PASS", case_id)

    def test_exposure_identity_not_timestamp(self) -> None:
        graph = identity_graph(
            {
                "experiment_id": "real-model-sol-vs-terra-v1",
                "assignment_id": "a1",
                "spawn_config_hash": "s",
                "worker_argv": ["hermes", "-m", "gpt-5.6-sol"],
                "session_id": "sess",
                "trace_id": "tr",
                "assigned_model": "gpt-5.6-sol",
                "observed_model": "gpt-5.6-sol",
            }
        )
        self.assertTrue(graph["ok"])
        self.assertEqual(graph["fidelity"], "MATCHED")
        self.assertFalse(graph["timestamp_only"])

    def test_real_evidence_can_recommend_without_activating(self) -> None:
        rec = recommend_from_result(
            {
                "source": "phase6",
                "experiment_id": "real-model-sol-vs-terra-v1",
                "conclusion": "EVIDENCE_FOR_CANDIDATE",
                "reason": "ITT interval excludes 0",
                "scope": "BENCHMARK",
                "treatment_dimension": "MODEL",
                "real_hermes_inference": True,
                "validity": {
                    "PROTOCOL_INTEGRITY": "PASS",
                    "ASSIGNMENT_INTEGRITY": "PASS",
                    "CONFIG_INTEGRITY": "PASS",
                    "ENVIRONMENT_INTEGRITY": "PASS",
                    "EXPOSURE_FIDELITY": "PASS",
                    "OUTCOME_COVERAGE": "PASS",
                    "EVALUATOR_COMPATIBILITY": "PASS",
                    "MEMORY_ISOLATION": "PASS",
                    "WORKSPACE_ISOLATION": "PASS",
                },
                "guardrail_state": "PASS",
            }
        )
        self.assertEqual(rec["classification"], "PRODUCTION_CANDIDATE")
        self.assertTrue(rec["production_promotable"])
        self.assertFalse(rec["auto_promote"])
        self.assertFalse(rec["active_policy"])


class ReadinessAndSecurityTests(unittest.TestCase):
    def test_cells_are_independent(self) -> None:
        values = cells()
        self.assertEqual(values["production_adaptation"], "DISABLED")
        self.assertEqual(values["secure_human_authority"], "READY_FOR_OPERATOR_BOOTSTRAP")
        self.assertEqual(values["real_causal_evidence"], "BLOCKED_BUDGET")
        self.assertNotEqual(values["memory_isolation"], values["approval_a"])
        named = cell("authority")
        self.assertEqual(named["cell"], "secure_human_authority")
        self.assertFalse(named["collapsed"])

    def test_canary_package_has_no_secret(self) -> None:
        package = generate_package(
            recommendation_id="r",
            policy_id="p",
            policy_hash="h",
            policy_version="1",
            candidate_config_hash="c",
            fallback_hash="f",
            rollback_hash="rb",
            expiry="2027-01-01T00:00:00+00:00",
            evidence={"status": "BLOCKED_EVIDENCE", "secret": FAKE_SECRET},
        )
        dest = Path(package["path"])
        blob = "\n".join(path.read_text(encoding="utf-8") for path in dest.iterdir())
        self.assertNotIn(FAKE_SECRET, blob)
        self.assertEqual(package["production_canary"], "NOT_EXECUTED")
        self.assertEqual(package["status"], "BLOCKED_EVIDENCE")


class ChaosSafetyTests(unittest.TestCase):
    def test_missing_memory_and_budget_and_authority(self) -> None:
        self.assertFalse(require_budget_authorization()["ok"])
        authority = verify_production_authorization()
        self.assertIn(authority["status"], {"BLOCKED_SECURITY_BOUNDARY", "PROTECTED_TRUST_PRESENT"})
        self.assertFalse(authority["granted"])
        result = resolve_spawn_configuration({"board": "missing"}, {"model": "base"}, state={"bindings": []})
        self.assertEqual(result["resolution"], "BASELINE")
