# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Handler and runtime tests for the url-authority check node (OMN-21520)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.url_authority_check.model_url_authority_check_input import (
    ModelUrlAuthorityCheckInput,
)
from omnibase_core.nodes.node_url_authority_check_compute.handler import (
    NodeUrlAuthorityCheckCompute,
)
from omnibase_core.nodes.node_url_authority_check_compute.runtime_url_authority_check import (
    main,
)
from omnibase_core.validation.validator_url_authority import (
    RULE_CONST_ASSIGNMENT,
    make_fingerprint,
)

pytestmark = pytest.mark.unit

_BAD_SNIPPET = 'BASE_URL = "https://api.new-host.io/v1"'


def _baseline(tmp_path: Path) -> Path:
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps({"schema_version": "1.0.0", "count": 0, "violations": []}),
        encoding="utf-8",
    )
    return baseline


def _args(path: Path, tmp_path: Path) -> list[str]:
    return [
        str(path),
        "--repo",
        "r",
        "--repo-root",
        str(tmp_path),
        "--baseline",
        str(_baseline(tmp_path)),
    ]


def test_handle_passes_clean_source() -> None:
    result = NodeUrlAuthorityCheckCompute().handle(
        ModelUrlAuthorityCheckInput(
            repo="r", files=(ModelSourceFile(path="mod.py", source="x = 1\n"),)
        )
    )
    assert result.violations == ()


def test_handle_flags_url_const_assignment() -> None:
    result = NodeUrlAuthorityCheckCompute().handle(
        ModelUrlAuthorityCheckInput(
            repo="r",
            files=(ModelSourceFile(path="mod.py", source=_BAD_SNIPPET + "\n"),),
        )
    )
    assert [(v.rule, v.path, v.line) for v in result.violations] == [
        (RULE_CONST_ASSIGNMENT, "mod.py", 1)
    ]
    assert result.violations[0].fingerprint == make_fingerprint(
        "r", "mod.py", _BAD_SNIPPET
    )


def test_main_exit_zero_on_clean(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "mod.py"
    path.write_text("x = 1\n", encoding="utf-8")
    assert main(_args(path, tmp_path)) == 0
    assert (
        "URL-AUTHORITY GATE PASSED: 0 new violations (0 grandfathered)."
        in capsys.readouterr().out
    )


def test_main_exit_one_on_new_violation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "mod.py"
    path.write_text(_BAD_SNIPPET + "\n", encoding="utf-8")
    assert main(_args(path, tmp_path)) == 1
    err = capsys.readouterr().err
    assert "URL-AUTHORITY GATE FAILED: 1 NEW violation(s)" in err
    assert f"[{RULE_CONST_ASSIGNMENT}] r/mod.py:1" in err
