# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Handler and runtime tests for node_literal_duplication_check_compute (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.nodes.literal_duplication_check.model_literal_duplication_check_input import (
    ModelLiteralDuplicationCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.nodes.node_literal_duplication_check_compute.handler import (
    NodeLiteralDuplicationCheckCompute,
)
from omnibase_core.nodes.node_literal_duplication_check_compute.runtime_literal_duplication_check import (
    main,
)

pytestmark = pytest.mark.unit

GOOD = "from typing import Literal\n\nMode = Literal['a', 'b']\n"
BAD = "from typing import Literal\n\nLiteralValidationLevel = Literal['BASIC']\n"


def test_handle_pass_and_fail() -> None:
    handler = NodeLiteralDuplicationCheckCompute()
    ok = handler.handle(
        ModelLiteralDuplicationCheckInput(
            files=(ModelSourceFile(path="a.py", source=GOOD),)
        )
    )
    assert ok.errors == ()
    bad = handler.handle(
        ModelLiteralDuplicationCheckInput(
            files=(ModelSourceFile(path="a.py", source=BAD),)
        )
    )
    assert len(bad.errors) == 1
    assert "a.py:3" in bad.errors[0]
    assert "EnumValidationLevel" in bad.errors[0]


def test_main_exit_codes(tmp_path: Path) -> None:
    good = tmp_path / "good.py"
    good.write_text(GOOD)
    bad = tmp_path / "bad.py"
    bad.write_text(BAD)
    assert main([str(good)]) == 0
    assert main([str(bad)]) == 1
    assert main([str(tmp_path / "missing.py")]) == 1
