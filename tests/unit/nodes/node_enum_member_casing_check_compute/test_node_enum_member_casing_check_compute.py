# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Handler and runtime tests for node_enum_member_casing_check_compute (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.nodes.enum_member_casing_check.model_enum_member_casing_check_input import (
    ModelEnumMemberCasingCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.nodes.node_enum_member_casing_check_compute.handler import (
    NodeEnumMemberCasingCheckCompute,
)
from omnibase_core.nodes.node_enum_member_casing_check_compute.runtime_enum_member_casing_check import (
    main,
)

pytestmark = pytest.mark.unit

GOOD = "from enum import Enum\n\n\nclass EnumA(Enum):\n    ACTIVE = 'a'\n"
BAD = "from enum import Enum\n\n\nclass EnumA(Enum):\n    active = 'a'\n"


def test_handle_pass_and_fail() -> None:
    handler = NodeEnumMemberCasingCheckCompute()
    ok = handler.handle(
        ModelEnumMemberCasingCheckInput(
            files=(ModelSourceFile(path="a.py", source=GOOD),)
        )
    )
    assert ok.issues == ()
    bad = handler.handle(
        ModelEnumMemberCasingCheckInput(
            files=(ModelSourceFile(path="a.py", source=BAD),)
        )
    )
    assert len(bad.issues) == 1
    assert "active" in bad.issues[0]
    assert "a.py" in bad.issues[0]


def test_main_exit_codes(tmp_path: Path) -> None:
    good = tmp_path / "good.py"
    good.write_text(GOOD)
    bad = tmp_path / "bad.py"
    bad.write_text(BAD)
    assert main([str(good)]) == 0
    assert main([str(bad)]) == 1
