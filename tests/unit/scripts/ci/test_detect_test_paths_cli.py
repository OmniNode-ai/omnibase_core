# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI integration tests for detect_test_paths entry point."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_cli_emits_valid_model_test_selection_json(tmp_path: Path) -> None:
    fake_diff = tmp_path / "diff.txt"
    fake_diff.write_text("src/omnibase_core/cli/foo.py\n")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.ci.detect_test_paths",
            "--changed-files-from",
            str(fake_diff),
            "--ref-name",
            "feature-branch",
            "--event-name",
            "pull_request",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["is_full_suite"] is False
    assert payload["full_suite_reason"] is None
    assert "tests/unit/cli/" in payload["selected_paths"]
    assert "matrix" in payload
    assert isinstance(payload["matrix"], list)


def test_cli_full_suite_on_main(tmp_path: Path) -> None:
    fake_diff = tmp_path / "diff.txt"
    fake_diff.write_text("src/omnibase_core/cli/foo.py\n")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.ci.detect_test_paths",
            "--changed-files-from",
            str(fake_diff),
            "--ref-name",
            "main",
            "--event-name",
            "push",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["is_full_suite"] is True
    assert payload["full_suite_reason"] == "main_branch"
    assert payload["split_count"] == 40
