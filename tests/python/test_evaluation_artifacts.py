"""Artifact capture tests. Never mutate production workspaces."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from engineering_os.evaluation.artifacts import (
    archive_commit,
    capture_tracked_patch,
    scan_bytes,
    tree_hash,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "evaluation" / "fixture_src"


def _git_repo() -> Path:
    dest = Path(tempfile.mkdtemp(prefix="eos-art-"))
    shutil.copytree(FIXTURE, dest, dirs_exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=dest, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=dest, check=True, capture_output=True)
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "fixture",
            "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_NAME": "fixture",
            "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        }
    )
    subprocess.run(["git", "commit", "-m", "init"], cwd=dest, check=True, capture_output=True, env=env)
    return dest


class ArtifactTests(unittest.TestCase):
    def test_commit_snapshot_hash_reproducible(self) -> None:
        repo = _git_repo()
        sha = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        first = archive_commit(repo, sha)
        second = archive_commit(repo, sha)
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.secret_scan_status, "PASS")
        self.assertEqual(first.method, "COMMIT_SNAPSHOT")
        shutil.rmtree(repo)

    def test_tracked_dirty_patch(self) -> None:
        repo = _git_repo()
        (repo / "src" / "app.py").write_text("def add(left, right):\n    return left + right + 0\n")
        result = capture_tracked_patch(repo)
        self.assertEqual(result.method, "BASE_COMMIT_PLUS_TRACKED_PATCH")
        self.assertEqual(result.secret_scan_status, "PASS")
        self.assertTrue(result.patch_hash)
        shutil.rmtree(repo)

    def test_untracked_required(self) -> None:
        repo = _git_repo()
        (repo / "new_module.py").write_text("print('hi')\n")
        result = capture_tracked_patch(repo, untracked_required=True)
        self.assertEqual(result.method, "UNTRACKED_REQUIRED")
        shutil.rmtree(repo)

    def test_secret_exclusion(self) -> None:
        self.assertEqual(scan_bytes(b"FAKE_PHASE4_SECRET_ABC123"), "FAIL")
        repo = _git_repo()
        (repo / "src" / "app.py").write_text("token='FAKE_PHASE4_SECRET_ABC123'\n")
        subprocess.run(["git", "add", "src/app.py"], cwd=repo, check=True, capture_output=True)
        env = os.environ.copy()
        env.update(
            {
                "GIT_AUTHOR_NAME": "fixture",
                "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                "GIT_COMMITTER_NAME": "fixture",
                "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
            }
        )
        subprocess.run(["git", "commit", "-m", "secret"], cwd=repo, check=True, capture_output=True, env=env)
        sha = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        result = archive_commit(repo, sha)
        self.assertEqual(result.secret_scan_status, "FAIL")
        shutil.rmtree(repo)

    def test_duplicate_hash(self) -> None:
        repo = _git_repo()
        sha = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        a = archive_commit(repo, sha)
        b = archive_commit(repo, sha)
        self.assertEqual(a.content_hash, b.content_hash)
        shutil.rmtree(repo)

    def test_tree_hash_stable(self) -> None:
        repo = _git_repo()
        self.assertEqual(tree_hash(repo), tree_hash(repo))
        shutil.rmtree(repo)


if __name__ == "__main__":
    unittest.main()
