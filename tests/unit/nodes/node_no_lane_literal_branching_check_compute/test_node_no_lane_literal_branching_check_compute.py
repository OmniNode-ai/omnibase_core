# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Handler and runtime tests for node_no_lane_literal_branching_check_compute."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.nodes.no_lane_literal_branching_check.model_no_lane_literal_branching_check_input import (
    ModelNoLaneLiteralBranchingCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.nodes.node_no_lane_literal_branching_check_compute.handler import (
    NodeNoLaneLiteralBranchingCheckCompute,
)
from omnibase_core.nodes.node_no_lane_literal_branching_check_compute.runtime_no_lane_literal_branching_check import (
    main,
)
from omnibase_core.validation.validator_no_lane_literal_branching import (
    RULE_LANE_LITERAL_COMPARE,
)

pytestmark = pytest.mark.unit

_BAD = 'if lane == "lane-a":\n    pass\n'
_CLEAN = "VALUE = 1\n"


def test_handle_reports_compare_finding() -> None:
    output = NodeNoLaneLiteralBranchingCheckCompute().handle(
        ModelNoLaneLiteralBranchingCheckInput(
            files=[
                ModelSourceFile(path="pkg/bad.py", source=_BAD),
                ModelSourceFile(path="pkg/ok.py", source=_CLEAN),
            ]
        )
    )
    assert [(v.path, v.line, v.rule) for v in output.violations] == [
        ("pkg/bad.py", 1, RULE_LANE_LITERAL_COMPARE)
    ]
    assert not output.is_clean


def test_handle_clean_input_is_clean() -> None:
    output = NodeNoLaneLiteralBranchingCheckCompute().handle(
        ModelNoLaneLiteralBranchingCheckInput(
            files=[ModelSourceFile(path="pkg/ok.py", source=_CLEAN)]
        )
    )
    assert output.violations == ()
    assert output.is_clean


def test_main_exit_codes(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text(_BAD, encoding="utf-8")
    clean = tmp_path / "clean.py"
    clean.write_text(_CLEAN, encoding="utf-8")
    assert main(["--repo-root", str(tmp_path), str(clean)]) == 0
    assert main(["--repo-root", str(tmp_path), str(bad)]) == 1
