# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from omnibase_core.gate.diff_hash import (
    DETERMINISTIC_DIFF_FLAGS,
    compute_config_hash,
    compute_diff_hash,
    compute_pr_diff_hash,
    compute_staged_diff_hash,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

pytestmark = pytest.mark.unit


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        check=True,
    )


def _init_repo(repo: Path) -> None:
    _run_git(repo, "init")
    _run_git(repo, "config", "user.email", "test@example.com")
    _run_git(repo, "config", "user.name", "Test User")


def _init_repo_with_staged_change(repo: Path) -> None:
    _init_repo(repo)
    (repo / "file.txt").write_text("hello\n", encoding="utf-8")
    _run_git(repo, "add", ".")


def _commit(repo: Path, message: str) -> str:
    _run_git(repo, "commit", "-m", message)
    return _run_git(repo, "rev-parse", "HEAD").stdout.decode("utf-8").strip()


def _sha256_prefixed(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


class TestComputeDiffHash:
    def test_returns_sha256_prefixed(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_repo_with_staged_change(repo)

        result = compute_staged_diff_hash(repo)

        assert result.startswith("sha256:")
        assert len(result) == 7 + 64

    def test_deterministic(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_repo_with_staged_change(repo)

        h1 = compute_staged_diff_hash(repo)
        h2 = compute_staged_diff_hash(repo)

        assert h1 == h2

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_repo_with_staged_change(repo)
        h1 = compute_staged_diff_hash(repo)

        (repo / "file.txt").write_text("world\n", encoding="utf-8")
        _run_git(repo, "add", "file.txt")
        h2 = compute_staged_diff_hash(repo)

        assert h1 != h2

    def test_staged_diff_hashes_exact_diff_bytes(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_repo_with_staged_change(repo)

        expected_diff = _run_git(
            repo,
            "diff",
            "--staged",
            *DETERMINISTIC_DIFF_FLAGS,
        ).stdout

        assert compute_staged_diff_hash(repo) == _sha256_prefixed(expected_diff)

    def test_pr_diff_hash_uses_explicit_base_and_head(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_repo(repo)
        (repo / "file.txt").write_text("base\n", encoding="utf-8")
        _run_git(repo, "add", ".")
        base_sha = _commit(repo, "base")
        (repo / "file.txt").write_text("head\n", encoding="utf-8")
        _run_git(repo, "add", ".")
        head_sha = _commit(repo, "head")

        expected_diff = _run_git(
            repo,
            "diff",
            *DETERMINISTIC_DIFF_FLAGS,
            f"{base_sha}...{head_sha}",
        ).stdout

        assert compute_pr_diff_hash(
            repo, base_sha=base_sha, head_sha=head_sha
        ) == _sha256_prefixed(expected_diff)

    def test_empty_staged_diff_fails_by_default(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_repo(repo)

        with pytest.raises(ModelOnexError, match="No staged diff found"):
            compute_staged_diff_hash(repo)

    def test_empty_pr_diff_fails_by_default(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_repo(repo)
        (repo / "file.txt").write_text("base\n", encoding="utf-8")
        _run_git(repo, "add", ".")
        head_sha = _commit(repo, "base")

        with pytest.raises(ModelOnexError, match="No PR diff found"):
            compute_pr_diff_hash(repo, base_sha=head_sha, head_sha=head_sha)

    def test_pr_diff_hash_does_not_fallback_to_staged_diff(
        self,
        tmp_path: Path,
    ) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_repo(repo)
        (repo / "file.txt").write_text("base\n", encoding="utf-8")
        _run_git(repo, "add", ".")
        head_sha = _commit(repo, "base")
        (repo / "local-only.txt").write_text("staged\n", encoding="utf-8")
        _run_git(repo, "add", "local-only.txt")

        with pytest.raises(ModelOnexError, match="No PR diff found"):
            compute_pr_diff_hash(repo, base_sha=head_sha, head_sha=head_sha)

    def test_allow_empty_hashes_empty_diff_bytes(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_repo(repo)

        assert compute_staged_diff_hash(repo, allow_empty=True) == _sha256_prefixed(b"")

    def test_base_and_head_refs_must_be_paired(self, tmp_path: Path) -> None:
        with pytest.raises(ModelOnexError, match="provided together"):
            compute_diff_hash(tmp_path, base_ref="abc123")


class TestComputeConfigHash:
    def test_hashes_config_file_bytes(self, tmp_path: Path) -> None:
        config_path = tmp_path / ".omnigate.yaml"
        content = b"version: 1.0.0\nproject_name: test\n"
        config_path.write_bytes(content)

        assert compute_config_hash(config_path) == _sha256_prefixed(content)

    def test_byte_level_changes_affect_config_hash(self, tmp_path: Path) -> None:
        config_path = tmp_path / ".omnigate.yaml"
        config_path.write_bytes(b"version: 1.0.0\n")
        h1 = compute_config_hash(config_path)

        config_path.write_bytes(b"version: 1.0.0\r\n")
        h2 = compute_config_hash(config_path)

        assert h1 != h2
