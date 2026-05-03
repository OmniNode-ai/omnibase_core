# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import pytest

from omnibase_core.analysis.semantic_diff import compute_diff
from omnibase_core.enums.enum_diff_severity import EnumChangeKind


@pytest.mark.unit
def test_compute_diff_zeroes_consumers_without_symbol_changes() -> None:
    source = "def unchanged() -> int:\n    return 1\n"
    report = compute_diff(source, source, "src/example.py", consumers_count=7)

    assert report.changes == ()
    assert report.total_consumers_affected == 0


@pytest.mark.unit
def test_compute_diff_does_not_refactor_unrelated_same_signature_symbols() -> None:
    old_source = "def alpha(value: int) -> int:\n    return value + 1\n"
    new_source = "def omega(value: int) -> int:\n    return value + 1\n"

    report = compute_diff(old_source, new_source, "src/example.py", consumers_count=3)

    kinds = {change.kind for change in report.changes}
    assert EnumChangeKind.REFACTOR not in kinds
    assert EnumChangeKind.DELETED_FUNCTION in kinds
    assert EnumChangeKind.NEW_FUNCTION in kinds
    assert report.total_consumers_affected == 3
