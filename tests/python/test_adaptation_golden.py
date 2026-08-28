"""Golden adaptation corpus. Expected outputs are authored, not inferred."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("EOS_EVAL_SANDBOX", "inline")
os.environ["EOS_ADAPTATION_RUNTIME"] = tempfile.mkdtemp(prefix="eos-adapt-test-")

from engineering_os.adaptation.approval import approve_production, sign_test, verify_test
from engineering_os.adaptation.canary import plan_canary, run_fixture_canary
from engineering_os.adaptation.compiler import CompileError, compile_policy, hash_bundle
from engineering_os.adaptation.guardrails import canary_health, evaluate as eval_guardrails
from engineering_os.adaptation.recommend import recommend_from_result
from engineering_os.adaptation.resolver import match_selector, resolve_policy, write_cache
from engineering_os.adaptation.rollback import next_binding, rollback_binding
from engineering_os.adaptation.schema import PolicyError, load_id, validate_raw
from engineering_os.adaptation.shadow import shadow_batch, shadow_decide


ROOT = Path(__file__).resolve().parents[2]

KNOWN_EFFECT = {
    "source": "phase6",
    "experiment_id": "fixture-known-effect-v1",
    "conclusion": "EVIDENCE_FOR_CANDIDATE",
    "reason": "ITT interval excludes 0. FIXTURE_VALIDATION_ONLY; not production causal evidence.",
    "scope": "FIXTURE",
    "treatment_dimension": "FIXTURE_ARTIFACT",
    "validity": {
        "PROTOCOL_INTEGRITY": "PASS",
        "ASSIGNMENT_INTEGRITY": "PASS",
        "CONFIG_INTEGRITY": "PASS",
        "ENVIRONMENT_INTEGRITY": "PASS",
        "EXPOSURE_FIDELITY": "PASS",
        "OUTCOME_COVERAGE": "PASS",
        "EVALUATOR_COMPATIBILITY": "PASS",
    },
    "guardrail_state": "PASS",
    "protocol_hash": "abc",
    "candidate_config_hash": "cand",
    "control_config_hash": "ctrl",
}


class RecommendTests(unittest.TestCase):
    def test_known_effect_is_test_only(self) -> None:
        rec = recommend_from_result(KNOWN_EFFECT)
        self.assertEqual(rec["classification"], "TEST_ONLY")
        self.assertFalse(rec["production_promotable"])
        self.assertEqual(rec["state"], "EVIDENCE_VALIDATED")
        self.assertFalse(rec["auto_promote"])
        self.assertFalse(rec["active_policy"])

    def test_aa_not_promotable(self) -> None:
        payload = dict(KNOWN_EFFECT)
        payload["experiment_id"] = "fixture-aa-v1"
        payload["conclusion"] = "NO_CLEAR_EFFECT"
        rec = recommend_from_result(payload)
        self.assertEqual(rec["classification"], "NOT_PROMOTABLE")

    def test_invalidated_blocked(self) -> None:
        payload = dict(KNOWN_EFFECT)
        payload["conclusion"] = "INVALIDATED"
        rec = recommend_from_result(payload)
        self.assertEqual(rec["state"], "NOT_PROMOTABLE")

    def test_guardrail_failure_blocked(self) -> None:
        payload = dict(KNOWN_EFFECT)
        payload["guardrail_state"] = "FAIL"
        rec = recommend_from_result(payload)
        self.assertEqual(rec["classification"], "NOT_PROMOTABLE")

    def test_phase5_cannot_recommend(self) -> None:
        rec = recommend_from_result({"source": "phase5", "conclusion": "EVIDENCE_FOR_CANDIDATE"})
        self.assertEqual(rec["classification"], "NOT_PROMOTABLE")
        self.assertIn("Phase 5", rec["reason"])

    def test_contamination_blocked(self) -> None:
        payload = dict(KNOWN_EFFECT)
        payload["contamination"] = True
        rec = recommend_from_result(payload)
        self.assertEqual(rec["classification"], "NOT_PROMOTABLE")


class PolicyTests(unittest.TestCase):
    def test_known_effect_policy_loads_and_hashes_stable(self) -> None:
        left = load_id("fixture-known-effect-policy-v1")
        right = load_id("fixture-known-effect-policy-v1")
        self.assertEqual(left["_policy_hash"], right["_policy_hash"])

    def test_rejects_arbitrary_command(self) -> None:
        data = load_id("fixture-known-effect-policy-v1")
        raw = {k: v for k, v in data.items() if not str(k).startswith("_")}
        raw["command"] = "rm -rf /"
        with self.assertRaises(PolicyError):
            validate_raw(raw)

    def test_compile_test_only(self) -> None:
        rec = recommend_from_result(KNOWN_EFFECT)
        compiled = compile_policy(rec, "fixture-known-effect-policy-v1")
        self.assertTrue(compiled["immutable"])
        self.assertEqual(compiled["classification"], "TEST_ONLY")
        self.assertEqual(hash_bundle(compiled["spec"]), compiled["policy_hash"])

    def test_cannot_compile_not_promotable(self) -> None:
        rec = recommend_from_result({**KNOWN_EFFECT, "conclusion": "NO_CLEAR_EFFECT"})
        with self.assertRaises(CompileError):
            compile_policy(rec, "fixture-known-effect-policy-v1")

    def test_cannot_escalate_fixture_to_production(self) -> None:
        rec = recommend_from_result(KNOWN_EFFECT)
        data = load_id("fixture-known-effect-policy-v1")
        raw = {k: v for k, v in data.items() if not str(k).startswith("_")}
        raw["scope"] = "PRODUCTION_FULL"
        with self.assertRaises(Exception):
            compile_policy(rec, raw)


class ApprovalTests(unittest.TestCase):
    def test_test_hmac_roundtrip(self) -> None:
        key = b"test-key-not-production"
        fields = {
            "stage": "A",
            "recommendation_id": "r1",
            "policy_hash": "h1",
            "policy_version": "1",
            "scope": "FIXTURE",
            "max_exposure": 4,
            "expires_at": "2027-01-01T00:00:00+00:00",
            "rollback_hash": "fb",
            "operator_identity": "tester",
        }
        sig = sign_test(fields, key=key)
        self.assertTrue(verify_test(fields, sig, key=key)["ok"])
        self.assertFalse(verify_test({**fields, "policy_hash": "other"}, sig, key=key)["ok"])

    def test_test_key_cannot_sign_production(self) -> None:
        with self.assertRaises(Exception):
            sign_test({"scope": "PRODUCTION_CANARY", "stage": "A"}, key=b"x")

    def test_production_approve_blocked(self) -> None:
        payload = approve_production()
        self.assertEqual(payload["status"], "BLOCKED_APPROVAL_BOUNDARY")
        self.assertFalse(payload["granted"])


class ResolverTests(unittest.TestCase):
    def _bundle(self, policy_id: str = "p1", mode: str = "CANARY") -> dict:
        spec = load_id("fixture-known-effect-policy-v1")
        return {
            "kill_switch": False,
            "bindings": [
                {
                    "policy_id": policy_id,
                    "policy_hash": spec["_policy_hash"],
                    "state": "ACTIVE",
                    "mode": mode,
                    "spec": spec,
                    "selectors": spec["selectors"],
                }
            ],
        }

    def test_fixture_context_selects_candidate(self) -> None:
        decision = resolve_policy(
            {"board": "eos-phase6-exp", "task_class": "fixture", "environment": "fixture", "scope": "FIXTURE"},
            self._bundle(),
        )
        self.assertEqual(decision["result"], "CANDIDATE")
        self.assertEqual(decision["resolution"], "CANDIDATE")

    def test_unmatched_is_not_eligible(self) -> None:
        decision = resolve_policy(
            {"board": "retropick-markets-release", "task_class": "production_kanban", "environment": "production"},
            self._bundle(),
        )
        self.assertEqual(decision["resolution"], "BASELINE")
        self.assertEqual(decision["result"], "NOT_ELIGIBLE")

    def test_kill_switch(self) -> None:
        state = self._bundle()
        state["kill_switch"] = True
        decision = resolve_policy(
            {"board": "eos-phase6-exp", "task_class": "fixture", "environment": "fixture"},
            state,
        )
        self.assertEqual(decision["resolution"], "BASELINE")
        self.assertEqual(decision["reason"], "GLOBAL_KILL_SWITCH")

    def test_conflict_same_priority(self) -> None:
        a = load_id("fixture-conflict-a-v1")
        b = load_id("fixture-conflict-b-v1")
        state = {
            "kill_switch": False,
            "bindings": [
                {"policy_id": "a", "state": "ACTIVE", "mode": "CANARY", "spec": a, "selectors": a["selectors"]},
                {"policy_id": "b", "state": "ACTIVE", "mode": "CANARY", "spec": b, "selectors": b["selectors"]},
            ],
        }
        decision = resolve_policy(
            {"board": "eos-phase6-exp", "task_class": "fixture"},
            state,
        )
        self.assertEqual(decision["result"], "CONFLICT")
        self.assertEqual(decision["resolution"], "BASELINE")

    def test_shadow_does_not_actuate(self) -> None:
        decision = resolve_policy(
            {"board": "eos-phase6-exp", "task_class": "fixture", "environment": "fixture"},
            self._bundle(mode="SHADOW"),
        )
        self.assertEqual(decision["result"], "CANDIDATE")
        self.assertEqual(decision["resolution"], "BASELINE")
        self.assertFalse(decision["actuate"])

    def test_corrupt_state_baselines(self) -> None:
        decision = resolve_policy({"board": "x"}, {"bindings": "not-a-list"})
        self.assertEqual(decision["resolution"], "BASELINE")

    def test_selector_unknown_op_does_not_match(self) -> None:
        self.assertFalse(match_selector({"match": "ALL", "conditions": [{"field": "board", "op": "REGEX", "values": [".*"]}]}, {"board": "x"}))


class ShadowTests(unittest.TestCase):
    def test_no_mutation(self) -> None:
        spec = load_id("fixture-known-effect-policy-v1")
        state = {"kill_switch": False, "bindings": [{"policy_id": "p", "state": "ACTIVE", "mode": "SHADOW", "spec": spec, "selectors": spec["selectors"]}]}
        batch = shadow_batch(
            [
                {"task_id": "t1", "board": "eos-phase6-exp", "task_class": "fixture", "environment": "fixture"},
                {"task_id": "t2", "board": "retropick-markets-release", "task_class": "production_kanban", "environment": "production"},
            ],
            state,
        )
        self.assertFalse(batch["mutated"])
        self.assertGreaterEqual(batch["would_change"], 1)
        self.assertFalse(shadow_decide({"task_id": "t1"}, state)["efficacy_claim"])


class GuardrailTests(unittest.TestCase):
    def test_bad_candidate_disables(self) -> None:
        exposures = [
            {"selected": "CANDIDATE", "outcome": {"quality_vector": {"tests": "FAIL"}}},
            {"selected": "BASELINE", "outcome": {"quality_vector": {"tests": "PASS"}}},
        ]
        guard = eval_guardrails(
            [{"id": "phase4.quality_vector.tests", "fail_on": "FAIL", "critical": True, "min_n": 1, "candidate_only": True}],
            exposures,
        )
        self.assertTrue(guard["auto_disable"])
        self.assertFalse(guard["auto_promote"])
        self.assertEqual(canary_health(guard, exposures), "CANARY_UNHEALTHY")

    def test_unknown_blocks_promotion(self) -> None:
        guard = eval_guardrails(
            [{"id": "phase4.quality_vector.tests", "fail_on": "FAIL", "critical": True, "min_n": 3, "candidate_only": True}],
            [{"selected": "CANDIDATE", "outcome": {"quality_vector": {}}}],
        )
        self.assertTrue(guard["promote_blocked"])
        self.assertFalse(guard["auto_promote"])

    def test_healthy(self) -> None:
        exposures = [{"selected": "CANDIDATE", "outcome": {"quality_vector": {"tests": "PASS"}}}]
        guard = eval_guardrails(
            [{"id": "phase4.quality_vector.tests", "fail_on": "FAIL", "critical": True, "min_n": 1, "candidate_only": True}],
            exposures,
        )
        self.assertEqual(canary_health(guard, exposures), "CANARY_HEALTHY")
        self.assertFalse(guard["auto_disable"])


class RollbackTests(unittest.TestCase):
    def test_cas_and_idempotent(self) -> None:
        current = {"binding_version": 3, "state": "ACTIVE", "mode": "CANARY", "fallback_config_hash": "fb"}
        first = rollback_binding(current, expected_version=3, reason="test", trigger="guardrail")
        self.assertEqual(first["binding_version_after"], 4)
        self.assertFalse(first["interrupt_running"])
        mismatch = next_binding(current, policy_hash="x", mode="CANARY", state="ACTIVE", binding_key="default", expected_version=9)
        self.assertEqual(mismatch["status"], "conflict")
        already = rollback_binding({"binding_version": 4, "state": "ROLLED_BACK", "mode": "BASELINE"}, expected_version=4, reason="again", trigger="operator")
        self.assertTrue(already["already_baseline"])
        self.assertTrue(already["idempotent"])


class GoldenFilesTests(unittest.TestCase):
    GOLDEN = ROOT / "tests" / "adaptation" / "golden"

    def _load(self, name: str) -> dict:
        import yaml

        return yaml.safe_load((self.GOLDEN / name).read_text(encoding="utf-8"))

    def test_golden_files_exist(self) -> None:
        required = (
            "known-effect-test-only.yaml",
            "aa-not-promotable.yaml",
            "production-approve-blocked.yaml",
            "kill-switch-baseline.yaml",
            "conflict-baseline.yaml",
            "bad-canary-unhealthy.yaml",
            "rollback-idempotent.yaml",
        )
        for name in required:
            self.assertTrue((self.GOLDEN / name).is_file(), name)

    def test_known_effect_golden_matches_engine(self) -> None:
        golden = self._load("known-effect-test-only.yaml")
        rec = recommend_from_result(KNOWN_EFFECT)
        self.assertEqual(rec["classification"], golden["expected_classification"])
        self.assertEqual(rec["state"], golden["expected_state"])
        self.assertEqual(rec["production_promotable"], golden["production_promotable"])
        self.assertEqual(rec["auto_promote"], golden["auto_promote"])

    def test_aa_golden_matches_engine(self) -> None:
        golden = self._load("aa-not-promotable.yaml")
        rec = recommend_from_result({**KNOWN_EFFECT, "experiment_id": golden["experiment_id"], "conclusion": golden["conclusion"]})
        self.assertEqual(rec["classification"], golden["expected_classification"])

    def test_production_approve_golden(self) -> None:
        golden = self._load("production-approve-blocked.yaml")
        payload = approve_production()
        self.assertEqual(payload["status"], golden["expected_status"])
        self.assertEqual(payload["granted"], golden["granted"])

    def test_kill_switch_golden(self) -> None:
        golden = self._load("kill-switch-baseline.yaml")
        spec = load_id("fixture-known-effect-policy-v1")
        state = {
            "kill_switch": golden["kill_switch"],
            "bindings": [{"policy_id": "p", "state": "ACTIVE", "mode": "CANARY", "spec": spec, "selectors": spec["selectors"]}],
        }
        decision = resolve_policy({"board": golden["board"], "task_class": golden["task_class"]}, state)
        self.assertEqual(decision["resolution"], golden["expected_resolution"])
        self.assertEqual(decision["reason"], golden["expected_reason"])


class CanaryPlanTests(unittest.TestCase):
    def test_default_concurrency_one(self) -> None:
        plan = plan_canary(load_id("fixture-known-effect-policy-v1"))
        self.assertEqual(plan["max_concurrent_candidate"], 1)
        self.assertFalse(plan["auto_promote"])

    def test_bounded_run_without_actuation_state(self) -> None:
        spec = load_id("fixture-known-effect-policy-v1")
        state = {
            "kill_switch": False,
            "bindings": [{"policy_id": spec["policy_id"], "state": "ACTIVE", "mode": "CANARY", "spec": spec, "selectors": spec["selectors"]}],
        }
        run = run_fixture_canary({"spec": spec}, units=["u0", "u1"], state=state, execute=False)
        self.assertLessEqual(run["candidate_n"], 1)
        self.assertEqual(run["max_concurrent_observed"], run["candidate_n"])
        self.assertFalse(run["auto_promote"])


if __name__ == "__main__":
    unittest.main()
