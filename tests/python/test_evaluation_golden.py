"""Golden evaluation corpus. Expected values are authored against EVALUATION_SEMANTICS.md."""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ["EOS_EVAL_SANDBOX"] = "inline"

from engineering_os.evaluation.artifacts import CaptureResult
from engineering_os.evaluation.compare import classify
from engineering_os.evaluation.eligibility import classify_task
from engineering_os.evaluation.engine import evaluate_capture, evaluate_trees, identity_hash
from engineering_os.evaluation.llm import FakeLLMEvaluator, production_judge
from engineering_os.evaluation.profiles import load_profile

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "evaluation" / "fixture_src"
GOLDEN = ROOT / "tests" / "evaluation" / "golden"


def _copy() -> Path:
    dest = Path(tempfile.mkdtemp(prefix="eos-golden-"))
    shutil.copytree(FIXTURE, dest, dirs_exist_ok=True)
    return dest


class ComparisonTests(unittest.TestCase):
    def test_four_primary_classes(self) -> None:
        self.assertEqual(classify("PASS", "PASS"), "UNCHANGED_PASS")
        self.assertEqual(classify("PASS", "FAIL"), "INTRODUCED_FAILURE")
        self.assertEqual(classify("FAIL", "PASS"), "FIXED_FAILURE")
        self.assertEqual(classify("FAIL", "FAIL"), "UNCHANGED_FAILURE")
        self.assertEqual(classify("UNKNOWN", "PASS"), "UNKNOWN")
        self.assertEqual(classify(None, "PASS"), "UNKNOWN")


class EligibilityTests(unittest.TestCase):
    def test_historical_without_sha_is_insufficient(self) -> None:
        decision = classify_task(
            {"id": "t_hist", "workspace_path": "/opt/retropick/.worktrees/t_hist"},
            git={"evidence_quality": "UNKNOWN"},
            cohort="production",
        )
        self.assertEqual(decision["eligibility"], "INSUFFICIENT_EVIDENCE")

    def test_available_sha_is_eligible(self) -> None:
        decision = classify_task(
            {"id": "t_ok"},
            git={"commit_sha": "abc1234", "evidence_quality": "AVAILABLE"},
            cohort="production",
        )
        self.assertEqual(decision["eligibility"], "ELIGIBLE")

    def test_fixture_runtime_is_test_eligible(self) -> None:
        decision = classify_task(
            {"id": "t_fix", "workspace_path": "/opt/hermes-engineering-os/.runtime/eval"},
            git={},
            cohort="fixture",
        )
        self.assertEqual(decision["eligibility"], "TEST_ELIGIBLE")


class GoldenEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = load_profile("fixture")

    def _eval(self, candidate: Path, baseline: Path | None = None, **kwargs):
        return evaluate_trees(candidate, self.profile, baseline=baseline, **kwargs)

    def test_clean_success(self) -> None:
        tree = _copy()
        payload = self._eval(tree, tree)
        self.assertEqual(payload["quality_vector"]["tests"], "PASS")
        self.assertEqual(payload["quality_vector"]["build"], "PASS")
        self.assertEqual(payload["comparisons"]["repo.tests"], "UNCHANGED_PASS")
        self.assertIn(payload["summary_state"], {"VERIFIED_PASS", "PARTIAL"})
        shutil.rmtree(tree)

    def test_introduced_test_regression(self) -> None:
        baseline = _copy()
        candidate = _copy()
        (candidate / "src" / "app.py").write_text("def add(left, right):\n    return left - right\n")
        payload = self._eval(candidate, baseline)
        self.assertEqual(payload["comparisons"]["repo.tests"], "INTRODUCED_FAILURE")
        self.assertEqual(payload["summary_state"], "VERIFIED_FAIL")
        shutil.rmtree(baseline)
        shutil.rmtree(candidate)

    def test_fixed_failure(self) -> None:
        baseline = _copy()
        candidate = _copy()
        (baseline / "src" / "app.py").write_text("def add(left, right):\n    return left - right\n")
        payload = self._eval(candidate, baseline)
        self.assertEqual(payload["comparisons"]["repo.tests"], "FIXED_FAILURE")
        shutil.rmtree(baseline)
        shutil.rmtree(candidate)

    def test_unchanged_failure(self) -> None:
        baseline = _copy()
        candidate = _copy()
        broken = "def add(left, right):\n    return left - right\n"
        (baseline / "src" / "app.py").write_text(broken)
        (candidate / "src" / "app.py").write_text(broken)
        payload = self._eval(candidate, baseline)
        self.assertEqual(payload["comparisons"]["repo.tests"], "UNCHANGED_FAILURE")
        shutil.rmtree(baseline)
        shutil.rmtree(candidate)

    def test_build_failure(self) -> None:
        tree = _copy()
        (tree / "src" / "app.py").write_text("def add(\n")
        payload = self._eval(tree, None)
        self.assertEqual(payload["quality_vector"]["build"], "FAIL")
        shutil.rmtree(tree)

    def test_lint_regression(self) -> None:
        baseline = _copy()
        candidate = _copy()
        text = (candidate / "src" / "app.py").read_text()
        (candidate / "src" / "app.py").write_text(text + "\n# LINT_VIOLATION\n")
        payload = self._eval(candidate, baseline)
        self.assertEqual(payload["comparisons"]["repo.lint"], "INTRODUCED_FAILURE")
        shutil.rmtree(baseline)
        shutil.rmtree(candidate)

    def test_preexisting_lint_is_warn(self) -> None:
        baseline = _copy()
        candidate = _copy()
        for tree in (baseline, candidate):
            text = (tree / "src" / "app.py").read_text()
            (tree / "src" / "app.py").write_text(text + "\n# LINT_VIOLATION\n")
        payload = self._eval(candidate, baseline)
        self.assertEqual(payload["comparisons"]["repo.lint"], "UNCHANGED_FAILURE")
        self.assertEqual(payload["quality_vector"]["lint"], "WARN")
        shutil.rmtree(baseline)
        shutil.rmtree(candidate)

    def test_typecheck_regression(self) -> None:
        baseline = _copy()
        candidate = _copy()
        (candidate / "scripts" / "broken.py").write_text("def oops(\n")
        payload = self._eval(candidate, baseline)
        self.assertEqual(payload["quality_vector"]["typecheck"], "FAIL")
        shutil.rmtree(baseline)
        shutil.rmtree(candidate)

    def test_architecture_violation(self) -> None:
        tree = _copy()
        (tree / "src" / "app.py").write_text("import forbidden_layer.db\n\ndef add(a, b):\n    return a + b\n")
        payload = self._eval(tree, tree)
        self.assertEqual(payload["quality_vector"]["architecture"], "FAIL")
        shutil.rmtree(tree)

    def test_scope_policy(self) -> None:
        baseline = _copy()
        candidate = _copy()
        vendor = candidate / "vendor"
        vendor.mkdir()
        (vendor / "hack.py").write_text("x = 1\n")
        payload = self._eval(candidate, baseline)
        self.assertEqual(payload["quality_vector"]["scope"], "FAIL")
        shutil.rmtree(baseline)
        shutil.rmtree(candidate)

    def test_security_secret(self) -> None:
        tree = _copy()
        (tree / "src" / "leak.py").write_text("token = 'FAKE_PHASE4_SECRET_ABC123'\n")
        payload = self._eval(tree, tree)
        self.assertEqual(payload["quality_vector"]["security"], "FAIL")
        shutil.rmtree(tree)

    def test_insufficient_evidence_not_scored(self) -> None:
        tree = _copy()
        payload = self._eval(tree, tree, eligibility="INSUFFICIENT_EVIDENCE")
        self.assertEqual(payload["summary_state"], "INSUFFICIENT_EVIDENCE")
        self.assertNotEqual(payload["quality_vector"]["tests"], "PASS")
        shutil.rmtree(tree)

    def test_missing_baseline_comparison_unknown(self) -> None:
        tree = _copy()
        payload = self._eval(tree, None)
        self.assertEqual(payload["comparisons"]["repo.tests"], "UNKNOWN")
        shutil.rmtree(tree)

    def test_timeout(self) -> None:
        tree = _copy()
        (tree / "tests" / "test_app.py").write_text(
            "import time, unittest\nclass T(unittest.TestCase):\n    def test_sleep(self):\n        time.sleep(30)\n"
        )
        from engineering_os.evaluation.sandbox import run_inline

        ran = run_inline(["python3", "-c", "import time; time.sleep(5)"], tree, timeout_seconds=1)
        self.assertTrue(ran.timeout)
        shutil.rmtree(tree)

    def test_github_blocked_auth_does_not_fail(self) -> None:
        tree = _copy()
        payload = self._eval(tree, tree, github_state="BLOCKED_AUTH")
        self.assertEqual(payload["quality_vector"]["ci"], "BLOCKED_AUTH")
        self.assertNotEqual(payload["summary_state"], "VERIFIED_FAIL")
        shutil.rmtree(tree)

    def test_acceptance_unknown(self) -> None:
        tree = _copy()
        payload = self._eval(tree, tree, task={"metadata": {"body": "please make it good"}})
        self.assertEqual(payload["quality_vector"]["acceptance"], "UNKNOWN")
        shutil.rmtree(tree)

    def test_llm_disabled_not_in_canonical_vector(self) -> None:
        tree = _copy()
        payload = self._eval(tree, tree)
        self.assertNotIn("llm", payload["quality_vector"])
        fake = FakeLLMEvaluator({"verdict": "PASS"}).evaluate("hash", "prompt")
        self.assertTrue(fake["experimental"])
        self.assertFalse(fake.get("canonical", False))
        disabled = production_judge().evaluate("hash", "prompt")
        self.assertEqual(disabled["verdict"], "NOT_APPLICABLE")
        shutil.rmtree(tree)

    def test_missing_candidate(self) -> None:
        expected = (GOLDEN / "missing-candidate.yaml").read_text()
        self.assertIn("INSUFFICIENT_EVIDENCE", expected)
        payload = self._eval(Path("/tmp/eos-missing-candidate-does-not-exist"), None)
        self.assertEqual(payload["summary_state"], "INSUFFICIENT_EVIDENCE")
        self.assertIn("missing candidate", payload["reason"])

    def test_process_crash(self) -> None:
        tree = _copy()
        from engineering_os.evaluation.sandbox import run_inline

        ran = run_inline(["python3", "-c", "import os; os.abort()"], tree)
        self.assertNotEqual(ran.exit_code, 0)
        shutil.rmtree(tree)

    def test_resource_exhaustion_maps_to_error(self) -> None:
        from engineering_os.evaluation.sandbox import SandboxResult
        from engineering_os.evaluation.engine import _command_result
        from unittest.mock import patch

        fake = SandboxResult(
            exit_code=137,
            stdout="",
            stderr="",
            duration_ms=10,
            timeout=False,
            resource_failure=True,
            image="inline",
            network="none",
        )
        with patch("engineering_os.evaluation.sandbox.run_command", return_value=fake):
            result = _command_result(["python3", "-c", "pass"], Path("."), 1)
        self.assertEqual(result["verdict"], "ERROR")

    def test_duplicate_identity_hash(self) -> None:
        tree = _copy()
        first = self._eval(tree, tree)
        second = self._eval(tree, tree)
        self.assertEqual(identity_hash(first), identity_hash(second))
        shutil.rmtree(tree)

    def test_stale_profile_version_changes_identity(self) -> None:
        tree = _copy()
        payload = self._eval(tree, tree)
        other = dict(payload)
        other["profile_version"] = "999"
        self.assertNotEqual(identity_hash(payload), identity_hash(other))
        shutil.rmtree(tree)

    def test_artifact_hash_mismatch(self) -> None:
        capture = CaptureResult(
            method="COMMIT_SNAPSHOT",
            content_hash="0" * 64,
            size_bytes=4,
            secret_scan_status="PASS",
            payload=b"abcd",
        )
        payload = evaluate_capture(capture, self.profile)
        self.assertEqual(payload["summary_state"], "INSUFFICIENT_EVIDENCE")
        self.assertIn("hash mismatch", payload["reason"])

    def test_golden_files_exist_for_required_cases(self) -> None:
        required = [
            "clean-success",
            "introduced-regression",
            "fixed-failure",
            "unchanged-failure",
            "build-failure",
            "lint-regression",
            "typecheck-regression",
            "architecture-violation",
            "scope-policy",
            "security-secret",
            "insufficient-evidence",
            "missing-baseline",
            "missing-candidate",
            "timeout",
            "process-crash",
            "resource-exhaustion",
            "duplicate-evaluation",
            "stale-evaluator-version",
            "hash-mismatch",
            "github-blocked-auth",
            "untracked-required",
        ]
        for name in required:
            path = GOLDEN / f"{name}.yaml"
            self.assertTrue(path.is_file(), name)
            self.assertTrue(path.read_text().strip())


if __name__ == "__main__":
    unittest.main()
