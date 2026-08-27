"""Golden phase3-v1 outcomes. Expected values are authored against OUTCOME_SEMANTICS.md."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from engineering_os.analytics.normalize import normalize_bundle
from engineering_os.analytics.rules import derive_outcome
from engineering_os.analytics.scope import load_scope

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "analytics" / "golden"
SCOPE = load_scope()


def _load_expected(path: Path) -> dict[str, object]:
    expected: dict[str, object] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.split("#", 1)[0].strip()
        if not stripped or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        expected[key.strip()] = _coerce(value.strip())
    return expected


def _coerce(value: str) -> object:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", ""}:
        return None
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)
    try:
        return float(value)
    except ValueError:
        return value


class GoldenAnalyticsTests(unittest.TestCase):
    def test_golden_corpus_matches_authored_semantics(self) -> None:
        cases = sorted(path for path in GOLDEN.iterdir() if path.is_dir())
        self.assertGreaterEqual(len(cases), 14)
        for case in cases:
            with self.subTest(case=case.name):
                raw = json.loads((case / "input.json").read_text(encoding="utf-8"))
                expected = _load_expected(case / "expected.yaml")
                bundle = normalize_bundle(raw, SCOPE)
                outcome = derive_outcome(bundle, SCOPE)
                for key, value in expected.items():
                    self.assertEqual(outcome.get(key), value, f"{case.name}.{key}")


if __name__ == "__main__":
    unittest.main()
