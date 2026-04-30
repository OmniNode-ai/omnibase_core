# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for EnumDiffSeverity, EnumChangeKind, ModelSymbolChange, ModelSemanticDiffReport."""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_diff_severity import EnumChangeKind, EnumDiffSeverity
from omnibase_core.models.analysis.model_semantic_diff_report import (
    ModelSemanticDiffReport,
)
from omnibase_core.models.analysis.model_symbol_change import ModelSymbolChange


def test_enum_diff_severity_members() -> None:
    assert {v.value for v in EnumDiffSeverity} == {"critical", "high", "medium", "low"}


def test_enum_diff_severity_is_str() -> None:
    assert isinstance(EnumDiffSeverity.CRITICAL, str)
    assert EnumDiffSeverity.CRITICAL.value == "critical"


def test_enum_change_kind_members() -> None:
    expected = {
        "signature_change",
        "api_change",
        "guard_removed",
        "deleted_function",
        "logic_change",
        "new_function",
        "refactor",
        "cosmetic",
    }
    assert {v.value for v in EnumChangeKind} == expected


def test_enum_change_kind_is_str() -> None:
    assert isinstance(EnumChangeKind.SIGNATURE_CHANGE, str)


def test_model_symbol_change_frozen() -> None:
    sc = ModelSymbolChange(
        kind=EnumChangeKind.SIGNATURE_CHANGE,
        severity=EnumDiffSeverity.HIGH,
        symbol_name="my_func",
        file_path="src/foo.py",
        consumers_count=3,
    )
    with pytest.raises(Exception):
        sc.symbol_name = "other"  # type: ignore[misc]  # NOTE(OMN-10371): intentional frozen-model mutation check


def test_model_symbol_change_fields() -> None:
    sc = ModelSymbolChange(
        kind=EnumChangeKind.GUARD_REMOVED,
        severity=EnumDiffSeverity.CRITICAL,
        symbol_name="validate_token",
        file_path="src/auth.py",
        consumers_count=10,
    )
    assert sc.kind == EnumChangeKind.GUARD_REMOVED
    assert sc.severity == EnumDiffSeverity.CRITICAL
    assert sc.symbol_name == "validate_token"
    assert sc.file_path == "src/auth.py"
    assert sc.consumers_count == 10


def test_model_semantic_diff_report_frozen() -> None:
    sc = ModelSymbolChange(
        kind=EnumChangeKind.NEW_FUNCTION,
        severity=EnumDiffSeverity.LOW,
        symbol_name="helper",
        file_path="src/utils.py",
        consumers_count=0,
    )
    report = ModelSemanticDiffReport(changes=(sc,), total_consumers_affected=0)
    with pytest.raises(Exception):
        report.total_consumers_affected = 5  # type: ignore[misc]  # NOTE(OMN-10371): intentional frozen-model mutation check


def test_model_semantic_diff_report_fields() -> None:
    sc1 = ModelSymbolChange(
        kind=EnumChangeKind.LOGIC_CHANGE,
        severity=EnumDiffSeverity.MEDIUM,
        symbol_name="process",
        file_path="src/core.py",
        consumers_count=2,
    )
    sc2 = ModelSymbolChange(
        kind=EnumChangeKind.DELETED_FUNCTION,
        severity=EnumDiffSeverity.HIGH,
        symbol_name="old_handler",
        file_path="src/core.py",
        consumers_count=5,
    )
    report = ModelSemanticDiffReport(changes=(sc1, sc2), total_consumers_affected=7)
    assert len(report.changes) == 2
    assert report.total_consumers_affected == 7
    assert report.changes[0].symbol_name == "process"


def test_model_semantic_diff_report_empty_changes() -> None:
    report = ModelSemanticDiffReport(changes=(), total_consumers_affected=0)
    assert report.changes == ()
    assert report.total_consumers_affected == 0
