# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import pytest

from omnibase_core.analysis.semantic_diff import compute_diff
from omnibase_core.enums.enum_diff_severity import EnumChangeKind, EnumDiffSeverity
from omnibase_core.models.analysis.model_semantic_diff_report import (
    ModelSemanticDiffReport,
)

pytestmark = pytest.mark.unit


def _kinds(report: ModelSemanticDiffReport) -> list[str]:
    return [c.kind for c in report.changes]


def _by_name(report: ModelSemanticDiffReport, name: str):
    return next((c for c in report.changes if c.symbol_name == name), None)


# --- new function ---


def test_new_function_detected():
    old = ""
    new = "def foo(x): return x\n"
    report = compute_diff(old, new, file_path="x.py", consumers_count=0)
    assert EnumChangeKind.NEW_FUNCTION in _kinds(report)
    change = _by_name(report, "foo")
    assert change is not None
    assert change.severity == EnumDiffSeverity.LOW


# --- deleted function ---


def test_deleted_function_detected():
    old = "def foo(x): return x\n"
    new = ""
    report = compute_diff(old, new, file_path="x.py", consumers_count=0)
    assert EnumChangeKind.DELETED_FUNCTION in _kinds(report)
    change = _by_name(report, "foo")
    assert change is not None
    assert change.severity == EnumDiffSeverity.HIGH


# --- signature change ---


def test_signature_change_detected():
    old = "def foo(x): return x\n"
    new = "def foo(x, y): return x + y\n"
    report = compute_diff(old, new, file_path="x.py", consumers_count=0)
    assert EnumChangeKind.SIGNATURE_CHANGE in _kinds(report)
    change = _by_name(report, "foo")
    assert change is not None
    assert change.severity == EnumDiffSeverity.HIGH


# --- logic change (body differs, signature same) ---


def test_logic_change_detected():
    old = "def foo(x):\n    return x\n"
    new = "def foo(x):\n    return x * 2\n"
    report = compute_diff(old, new, file_path="x.py", consumers_count=0)
    assert EnumChangeKind.LOGIC_CHANGE in _kinds(report)
    change = _by_name(report, "foo")
    assert change is not None
    assert change.severity == EnumDiffSeverity.MEDIUM


def test_one_line_body_only_change_is_logic_change():
    old = "def foo(x): return x\n"
    new = "def foo(x): return x * 2\n"
    report = compute_diff(old, new, file_path="x.py", consumers_count=0)
    assert EnumChangeKind.SIGNATURE_CHANGE not in _kinds(report)
    change = _by_name(report, "foo")
    assert change is not None
    assert change.kind == EnumChangeKind.LOGIC_CHANGE


# --- no change (same body + signature) ---


def test_no_change_produces_no_entry():
    src = "def foo(x):\n    return x\n"
    report = compute_diff(src, src, file_path="x.py", consumers_count=0)
    assert _by_name(report, "foo") is None


# --- guard_removed: name matches guard pattern ---


def test_guard_removed_on_guard_name():
    old = "def validate_token(token):\n    if not token: raise ValueError\n"
    new = ""
    report = compute_diff(old, new, file_path="x.py", consumers_count=0)
    change = _by_name(report, "validate_token")
    assert change is not None
    assert change.kind == EnumChangeKind.GUARD_REMOVED
    assert change.severity == EnumDiffSeverity.CRITICAL


def test_guard_removed_check_prefix():
    old = "def check_permissions(user):\n    pass\n"
    new = ""
    report = compute_diff(old, new, file_path="x.py", consumers_count=0)
    change = _by_name(report, "check_permissions")
    assert change is not None
    assert change.kind == EnumChangeKind.GUARD_REMOVED


def test_guard_removed_ensure_prefix():
    old = "def ensure_authenticated(req):\n    pass\n"
    new = ""
    report = compute_diff(old, new, file_path="x.py", consumers_count=0)
    assert _by_name(report, "ensure_authenticated").kind == EnumChangeKind.GUARD_REMOVED


def test_guard_removed_assert_prefix():
    old = "def assert_invariant(x):\n    pass\n"
    new = ""
    report = compute_diff(old, new, file_path="x.py", consumers_count=0)
    assert _by_name(report, "assert_invariant").kind == EnumChangeKind.GUARD_REMOVED


def test_non_guard_delete_is_deleted_function_not_guard():
    old = "def process_data(x):\n    pass\n"
    new = ""
    report = compute_diff(old, new, file_path="x.py", consumers_count=0)
    change = _by_name(report, "process_data")
    assert change.kind == EnumChangeKind.DELETED_FUNCTION


# --- rename detection ---


def test_rename_detected_same_signature_similar_line_count():
    # Same signature and body (just name changes) — should pair as rename
    old = "def foo(x):\n    return x\n"
    new = "def bar(x):\n    return x\n"
    report = compute_diff(old, new, file_path="x.py", consumers_count=0)
    # foo is removed, bar is added — should be merged as a rename (refactor)
    change = _by_name(report, "bar")
    assert change is not None
    assert change.kind == EnumChangeKind.REFACTOR


def test_rename_not_detected_when_line_count_diverges_too_much():
    # bar has very different body size — no rename, should be separate add/delete
    old = "def foo(x):\n    return x\n"
    new = (
        "def bar(x):\n"
        "    y = x * 2\n"
        "    z = y + 1\n"
        "    w = z - 3\n"
        "    v = w / 2\n"
        "    return v\n"
    )
    report = compute_diff(old, new, file_path="x.py", consumers_count=0)
    # foo should be a delete, bar should be a new function (not rename)
    foo_change = _by_name(report, "foo")
    bar_change = _by_name(report, "bar")
    assert foo_change is not None
    assert bar_change is not None
    assert bar_change.kind == EnumChangeKind.NEW_FUNCTION


# --- consumers_count is carried through ---


def test_consumers_count_on_deleted():
    old = "def foo(x): return x\n"
    new = ""
    report = compute_diff(old, new, file_path="x.py", consumers_count=5)
    change = _by_name(report, "foo")
    assert change is not None
    assert change.consumers_count == 5


def test_total_consumers_affected():
    old = "def foo(x): return x\ndef bar(y): return y\n"
    new = ""
    report = compute_diff(old, new, file_path="x.py", consumers_count=3)
    assert report.total_consumers_affected == 3


def test_negative_consumers_count_rejected():
    with pytest.raises(ValueError, match="consumers_count"):
        compute_diff("", "", file_path="x.py", consumers_count=-1)


# --- return type is correct ---


def test_returns_model_semantic_diff_report():
    old = "def foo(x): return x\n"
    new = "def foo(x, y): return x + y\n"
    report = compute_diff(old, new, file_path="x.py", consumers_count=0)
    assert isinstance(report, ModelSemanticDiffReport)
    assert isinstance(report.changes, tuple)


# --- file_path is propagated ---


def test_file_path_in_changes():
    old = "def foo(x): return x\n"
    new = "def foo(x, y): return x + y\n"
    report = compute_diff(old, new, file_path="src/foo.py", consumers_count=0)
    for change in report.changes:
        assert change.file_path == "src/foo.py"
