# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Integration tests for antipattern_checker CLI module (OMN-11923)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def _run_checker(
    *args: str, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "omnibase_core.validation.antipattern_checker", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
        check=False,
    )


@pytest.mark.unit
class TestAntipatternCheckerVersion:
    def test_outputs_registry_version(self, tmp_path: Path) -> None:
        clean_file = tmp_path / "clean.py"
        clean_file.write_text('"""Module with no issues."""\n\nx = 1\n')
        result = _run_checker(str(clean_file))
        assert "1.0.0" in result.stdout or "1.0.0" in result.stderr

    def test_outputs_registry_hash(self, tmp_path: Path) -> None:
        clean_file = tmp_path / "clean.py"
        clean_file.write_text('"""Module with no issues."""\n\nx = 1\n')
        result = _run_checker(str(clean_file))
        combined = result.stdout + result.stderr
        # sha256 hash is a 64-hex-char string; check a fragment appears
        import re

        assert re.search(r"[0-9a-f]{8,}", combined), "Expected hash in output"


@pytest.mark.unit
class TestAntipatternCheckerCleanFiles:
    def test_clean_file_exits_zero(self, tmp_path: Path) -> None:
        clean_file = tmp_path / "clean.py"
        clean_file.write_text('"""Module with no issues."""\n\nx = 1\n')
        result = _run_checker(str(clean_file))
        assert result.returncode == 0

    def test_no_files_exits_zero(self) -> None:
        result = _run_checker()
        assert result.returncode == 0

    def test_nonexistent_file_exits_zero(self) -> None:
        # Pre-commit may pass a deleted file; checker should skip gracefully
        result = _run_checker("/nonexistent/path/file.py")
        assert result.returncode == 0


@pytest.mark.unit
class TestAntipatternCheckerViolations:
    def test_sycophancy_in_docstring_exits_nonzero(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "sycophantic.py"
        bad_file.write_text(
            'def foo():\n    """Great, here is the implementation.\n\n    Args:\n        None\n    """\n    pass\n'
        )
        result = _run_checker(str(bad_file))
        assert result.returncode != 0

    def test_sycophancy_violation_mentions_rule_name(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "sycophantic.py"
        bad_file.write_text(
            'def foo():\n    """Great, here is the implementation."""\n    pass\n'
        )
        result = _run_checker(str(bad_file))
        assert "sycophancy" in result.stdout or "sycophancy" in result.stderr

    def test_hardcoded_ip_grep_pattern_exits_nonzero(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "hardcoded.py"
        bad_file.write_text('HOST = "192.168.1.100"\n')
        result = _run_checker(str(bad_file))
        assert result.returncode != 0

    def test_suppression_annotation_clears_violation(self, tmp_path: Path) -> None:
        suppressed_file = tmp_path / "suppressed.py"
        # The sycophancy entry has suppression_annotation "ai-slop-ok"
        suppressed_file.write_text(
            'def foo():\n    """Great, here is the implementation."""  # ai-slop-ok\n    return 1\n'
        )
        result = _run_checker(str(suppressed_file))
        assert result.returncode == 0

    def test_non_python_file_skipped_by_python_glob(self, tmp_path: Path) -> None:
        md_file = tmp_path / "readme.md"
        # sycophancy only applies to *.py files
        md_file.write_text("Great, here is the documentation.\n")
        result = _run_checker(str(md_file))
        assert result.returncode == 0

    def test_output_contains_file_and_line(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.py"
        bad_file.write_text(
            'def foo():\n    """Great, this is the implementation."""\n    pass\n'
        )
        result = _run_checker(str(bad_file))
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "bad.py" in combined


@pytest.mark.unit
class TestAntipatternCheckerSemanticSkipped:
    def test_semantic_rules_not_checked_offline(self, tmp_path: Path) -> None:
        # Create a file that would semantically match "handler_imports_handler" etc.
        # but has no static pattern to match — checker must not flag it
        suspect_file = tmp_path / "handler_example.py"
        suspect_file.write_text(
            "# handler_imports_handler example\nfrom mypackage.handlers import handler_b\n"
        )
        result = _run_checker(str(suspect_file))
        # Semantic rules require vector search; offline checker must not flag them
        combined = result.stdout + result.stderr
        assert "handler_imports_handler" not in combined


@pytest.mark.unit
class TestAntipatternCheckerPerformance:
    def test_runs_in_under_five_seconds(self, tmp_path: Path) -> None:
        import time

        files = []
        for i in range(20):
            f = tmp_path / f"module_{i}.py"
            f.write_text(f'"""Module {i}."""\n\nX = {i}\n')
            files.append(str(f))

        start = time.monotonic()
        result = _run_checker(*files)
        elapsed = time.monotonic() - start
        assert elapsed < 5.0, f"Checker took {elapsed:.1f}s (limit: 5s)"
        assert result.returncode == 0
