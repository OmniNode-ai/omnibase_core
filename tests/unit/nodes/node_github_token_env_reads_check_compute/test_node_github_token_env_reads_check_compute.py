# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Handler and runtime tests for node_github_token_env_reads_check_compute."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_github_token_scan_request import (
    ModelGithubTokenScanRequest,
)
from omnibase_core.nodes.node_github_token_env_reads_check_compute.handler import (
    NodeGithubTokenEnvReadsCheckCompute,
)
from omnibase_core.nodes.node_github_token_env_reads_check_compute.runtime_github_token_env_reads_check import (
    main,
)

pytestmark = pytest.mark.unit

_BAD = 'import os\ntoken = os.environ["GH_PAT"]\n'
_CLEAN = "x = 1\n"


def test_handle_reports_violation_and_skips_allowlisted() -> None:
    result = NodeGithubTokenEnvReadsCheckCompute().handle(
        ModelGithubTokenScanRequest(
            files={"src/a.py": _BAD, "src/b.py": _CLEAN, "tests/c.py": _BAD}
        )
    )
    assert [(v.file_path, v.line_number) for v in result.violations] == [
        ("src/a.py", 2)
    ]
    assert result.files_scanned == 2
    assert result.files_skipped == 1
    assert not result.is_clean


def test_handle_clean_input_is_clean() -> None:
    result = NodeGithubTokenEnvReadsCheckCompute().handle(
        ModelGithubTokenScanRequest(files={"src/b.py": _CLEAN})
    )
    assert result.is_clean
    assert result.files_scanned == 1


def test_main_exit_codes(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text(_BAD, encoding="utf-8")
    clean = tmp_path / "clean.py"
    clean.write_text(_CLEAN, encoding="utf-8")
    assert main([str(clean)]) == 0
    assert main([str(bad)]) == 1
    assert main([str(bad), "--report"]) == 0
    assert main([]) == 0
