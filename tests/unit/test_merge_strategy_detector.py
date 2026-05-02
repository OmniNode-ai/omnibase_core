# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for merge strategy detection and rebase conflict handling.

Tests cover:
- MergeStrategyDetector detection for queue and non-queue repos
- In-memory caching behaviour
- Fallback to SQUASH_AUTO on API errors and timeouts
- get_merge_command producing correct ``gh pr merge`` invocations
- GitHubMergeQueueAdapter strategy-aware dispatch
- RebaseResult factory helpers
- attempt_rebase success / conflict / timeout paths
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from omnibase_core.adapters.github_merge_queue_adapter import GitHubMergeQueueAdapter
from omnibase_core.adapters.merge_strategy_detector import MergeStrategyDetector
from omnibase_core.adapters.rebase_handler import RebaseResult, attempt_rebase
from omnibase_core.enums.enum_merge_strategy import EnumMergeStrategy

pytestmark = pytest.mark.unit


def _mock_run(stdout: str = "", returncode: int = 0, stderr: str = "") -> MagicMock:
    m = MagicMock()
    m.stdout = stdout
    m.stderr = stderr
    m.returncode = returncode
    return m


def _queue_protection_json() -> str:
    return json.dumps({"required_status_checks": {"strict": True, "contexts": []}})


def _non_queue_protection_json() -> str:
    return json.dumps({"required_status_checks": {"strict": False, "contexts": []}})


class TestMergeStrategyEnum:
    def test_merge_queue_value(self) -> None:
        assert EnumMergeStrategy.MERGE_QUEUE.value == "merge_queue"

    def test_squash_auto_value(self) -> None:
        assert EnumMergeStrategy.SQUASH_AUTO.value == "squash_auto"

    def test_string_comparison(self) -> None:
        assert EnumMergeStrategy.MERGE_QUEUE == "merge_queue"
        assert EnumMergeStrategy.SQUASH_AUTO == "squash_auto"


class TestMergeStrategyDetector:
    def setup_method(self) -> None:
        MergeStrategyDetector.clear_cache()

    def test_detects_merge_queue_repo(self) -> None:
        MergeStrategyDetector.clear_cache()
        detector = MergeStrategyDetector("OmniNode-ai", "omnibase_core")
        with patch("subprocess.run", return_value=_mock_run(_queue_protection_json())):
            assert detector.detect() == EnumMergeStrategy.MERGE_QUEUE

    def test_detects_squash_auto_repo(self) -> None:
        MergeStrategyDetector.clear_cache()
        detector = MergeStrategyDetector("OmniNode-ai", "omnidash")
        with patch(
            "subprocess.run", return_value=_mock_run(_non_queue_protection_json())
        ):
            assert detector.detect() == EnumMergeStrategy.SQUASH_AUTO

    def test_caches_result(self) -> None:
        MergeStrategyDetector.clear_cache()
        detector = MergeStrategyDetector("OmniNode-ai", "omnibase_core")
        with patch(
            "subprocess.run", return_value=_mock_run(_queue_protection_json())
        ) as mock_run:
            detector.detect()
            detector.detect()
        assert mock_run.call_count == 1

    def test_fallback_on_api_error(self) -> None:
        MergeStrategyDetector.clear_cache()
        detector = MergeStrategyDetector("OmniNode-ai", "private-repo")
        with patch(
            "subprocess.run", return_value=_mock_run(returncode=1, stderr="404")
        ):
            assert detector.detect() == EnumMergeStrategy.SQUASH_AUTO

    def test_fallback_on_timeout(self) -> None:
        MergeStrategyDetector.clear_cache()
        detector = MergeStrategyDetector("OmniNode-ai", "slow-repo")
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("gh", 10)):
            assert detector.detect() == EnumMergeStrategy.SQUASH_AUTO

    def test_fallback_on_json_error(self) -> None:
        MergeStrategyDetector.clear_cache()
        detector = MergeStrategyDetector("OmniNode-ai", "bad-json-repo")
        with patch("subprocess.run", return_value=_mock_run("not json")):
            assert detector.detect() == EnumMergeStrategy.SQUASH_AUTO

    def test_fallback_on_os_error(self) -> None:
        MergeStrategyDetector.clear_cache()
        detector = MergeStrategyDetector("OmniNode-ai", "no-gh-repo")
        with patch("subprocess.run", side_effect=OSError("gh not found")):
            assert detector.detect() == EnumMergeStrategy.SQUASH_AUTO

    def test_separate_cache_per_repo(self) -> None:
        MergeStrategyDetector.clear_cache()
        d1 = MergeStrategyDetector("OmniNode-ai", "omnibase_core")
        d2 = MergeStrategyDetector("OmniNode-ai", "omnidash")
        with patch(
            "subprocess.run",
            side_effect=[
                _mock_run(_queue_protection_json()),
                _mock_run(_non_queue_protection_json()),
            ],
        ):
            assert d1.detect() == EnumMergeStrategy.MERGE_QUEUE
            assert d2.detect() == EnumMergeStrategy.SQUASH_AUTO


class TestGetMergeCommand:
    def setup_method(self) -> None:
        MergeStrategyDetector.clear_cache()

    def test_merge_queue_command(self) -> None:
        detector = MergeStrategyDetector("OmniNode-ai", "omnibase_core")
        with patch("subprocess.run", return_value=_mock_run(_queue_protection_json())):
            cmd = detector.get_merge_command(42)
        assert cmd == ["gh", "pr", "merge", "42", "--auto"]

    def test_squash_auto_command(self) -> None:
        detector = MergeStrategyDetector("OmniNode-ai", "omnidash")
        with patch(
            "subprocess.run", return_value=_mock_run(_non_queue_protection_json())
        ):
            cmd = detector.get_merge_command(99)
        assert cmd == ["gh", "pr", "merge", "99", "--squash", "--auto"]


class TestRebaseResult:
    def test_ok_factory(self) -> None:
        r = RebaseResult.ok("done")
        assert r.success is True
        assert r.skipped is False
        assert r.needs_manual is False
        assert r.message == "done"

    def test_skip_factory(self) -> None:
        r = RebaseResult.skip("already ahead")
        assert r.success is False
        assert r.skipped is True
        assert r.needs_manual is False

    def test_manual_factory(self) -> None:
        r = RebaseResult.manual("conflicts")
        assert r.success is False
        assert r.skipped is False
        assert r.needs_manual is True

    def test_equality(self) -> None:
        assert RebaseResult.ok("x") == RebaseResult.ok("x")
        assert RebaseResult.ok("x") != RebaseResult.ok("y")
        assert RebaseResult.ok("x") != RebaseResult.manual("x")

    def test_repr(self) -> None:
        assert "ok" in repr(RebaseResult.ok("done"))
        assert "skip" in repr(RebaseResult.skip("skipped"))
        assert "manual" in repr(RebaseResult.manual("conflict"))


class TestGitHubMergeQueueAdapter:
    def setup_method(self) -> None:
        MergeStrategyDetector.clear_cache()

    def test_enqueue_uses_queue_strategy(self) -> None:
        detector = MergeStrategyDetector("OmniNode-ai", "omnibase_core")
        with patch("subprocess.run", return_value=_mock_run(_queue_protection_json())):
            detector.detect()
        adapter = GitHubMergeQueueAdapter(
            "OmniNode-ai", "omnibase_core", strategy_detector=detector
        )
        with patch("subprocess.run", return_value=_mock_run(returncode=0)) as mock_run:
            assert adapter.enqueue(10) is True
        cmd = mock_run.call_args[0][0]
        assert "--auto" in cmd
        assert "--squash" not in cmd

    def test_enqueue_uses_squash_strategy(self) -> None:
        detector = MergeStrategyDetector("OmniNode-ai", "omnidash")
        with patch(
            "subprocess.run", return_value=_mock_run(_non_queue_protection_json())
        ):
            detector.detect()
        adapter = GitHubMergeQueueAdapter(
            "OmniNode-ai", "omnidash", strategy_detector=detector
        )
        with patch("subprocess.run", return_value=_mock_run(returncode=0)) as mock_run:
            assert adapter.enqueue(10) is True
        cmd = mock_run.call_args[0][0]
        assert "--squash" in cmd
        assert "--auto" in cmd

    def test_enqueue_returns_false_on_failure(self) -> None:
        detector = MergeStrategyDetector("OmniNode-ai", "omnibase_core")
        with patch("subprocess.run", return_value=_mock_run(_queue_protection_json())):
            detector.detect()
        adapter = GitHubMergeQueueAdapter(
            "OmniNode-ai", "omnibase_core", strategy_detector=detector
        )
        with patch(
            "subprocess.run", return_value=_mock_run(returncode=1, stderr="error")
        ):
            assert adapter.enqueue(10) is False

    def test_enqueue_handles_timeout(self) -> None:
        detector = MergeStrategyDetector("OmniNode-ai", "omnibase_core")
        with patch("subprocess.run", return_value=_mock_run(_queue_protection_json())):
            detector.detect()
        adapter = GitHubMergeQueueAdapter(
            "OmniNode-ai", "omnibase_core", strategy_detector=detector
        )
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("gh", 10)):
            assert adapter.enqueue(10) is False

    def test_adapter_creates_detector_when_none_supplied(self) -> None:
        adapter = GitHubMergeQueueAdapter("OmniNode-ai", "omnibase_core")
        assert adapter._detector.owner == "OmniNode-ai"
        assert adapter._detector.repo == "omnibase_core"


class TestAttemptRebase:
    def test_successful_rebase(self) -> None:
        with patch(
            "subprocess.run",
            side_effect=[
                _mock_run(returncode=0),
                _mock_run(returncode=0, stdout="Rebasing... done"),
            ],
        ):
            result = attempt_rebase(Path("/repo"), "feature-branch")
        assert result.success is True
        assert "Rebased" in result.message

    def test_fetch_failure(self) -> None:
        with patch(
            "subprocess.run",
            return_value=_mock_run(returncode=1, stderr="network error"),
        ):
            result = attempt_rebase(Path("/repo"), "feature-branch")
        assert result.needs_manual is True
        assert "fetch failed" in result.message

    def test_conflict_during_rebase(self) -> None:
        with patch(
            "subprocess.run",
            side_effect=[
                _mock_run(returncode=0),
                _mock_run(returncode=1, stderr="CONFLICT: merge conflict"),
                _mock_run(returncode=0),
            ],
        ):
            result = attempt_rebase(Path("/repo"), "feature-branch")
        assert result.needs_manual is True
        assert "conflict" in result.message.lower()

    def test_rebase_timeout(self) -> None:
        with patch(
            "subprocess.run",
            side_effect=[
                _mock_run(returncode=0),
                subprocess.TimeoutExpired("git", 60),
                _mock_run(returncode=0),
            ],
        ):
            result = attempt_rebase(Path("/repo"), "feature-branch")
        assert result.needs_manual is True
        assert "timed out" in result.message

    def test_non_conflict_failure_aborts(self) -> None:
        with patch(
            "subprocess.run",
            side_effect=[
                _mock_run(returncode=0),
                _mock_run(returncode=1, stderr="some other error"),
                _mock_run(returncode=0),
            ],
        ):
            result = attempt_rebase(Path("/repo"), "feature-branch")
        assert result.needs_manual is True
        assert "failed" in result.message.lower()
