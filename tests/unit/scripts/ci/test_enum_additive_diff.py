# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-16321: structural proof that an ``enums/`` diff only APPENDS members.

The classifier is a governed safety surface: it must answer ``True`` for the
exact shape that motivated the ticket (OMN-16998 — two members appended to an
existing enum) and ``False`` for every shape that can change the meaning of an
existing member, plus every shape it cannot parse.
"""

from __future__ import annotations

import pytest

from scripts.ci.enum_additive_diff import (
    classify_enum_diff_additive,
    enum_module_shape,
)

BASE = '''"""Terminal failure causes."""

from enum import StrEnum


class EnumTerminalFailureCause(StrEnum):
    """Why a delegation terminated."""

    PROVIDER_QUOTA_EXHAUSTED = "provider_quota_exhausted"
    PROVIDER_TIMEOUT = "provider_timeout"

    def is_retryable(self) -> bool:
        return self is EnumTerminalFailureCause.PROVIDER_TIMEOUT
'''


def _mutate(old: str, new: str) -> str:
    assert old in BASE, f"fixture drift: {old!r} not in BASE"
    return BASE.replace(old, new)


# --- the shape this ticket exists for -------------------------------------


def test_appending_two_members_is_additive() -> None:
    """OMN-16998's exact diff shape: two members appended, nothing else edited."""
    head = _mutate(
        '    PROVIDER_TIMEOUT = "provider_timeout"\n',
        '    PROVIDER_TIMEOUT = "provider_timeout"\n'
        '    AUTH_FAILED = "auth_failed"\n'
        '    PROVIDER_UNAVAILABLE = "provider_unavailable"\n',
    )
    assert classify_enum_diff_additive(BASE, head) is True


def test_unchanged_file_is_additive() -> None:
    """The empty addition is still an addition — never a reason to escalate."""
    assert classify_enum_diff_additive(BASE, BASE) is True


def test_brand_new_enum_module_is_additive() -> None:
    """No base revision means nothing pre-existing can have been broken."""
    assert classify_enum_diff_additive(None, BASE) is True


# --- every shape that must still escalate ---------------------------------


def test_member_rename_escalates() -> None:
    head = _mutate("PROVIDER_TIMEOUT = ", "PROVIDER_TIMED_OUT = ")
    assert classify_enum_diff_additive(BASE, head) is False


def test_member_removal_escalates() -> None:
    head = _mutate('    PROVIDER_TIMEOUT = "provider_timeout"\n', "")
    assert classify_enum_diff_additive(BASE, head) is False


def test_member_value_change_escalates() -> None:
    """The persisted-value hazard: same name, different wire value."""
    head = _mutate('"provider_timeout"', '"timeout"')
    assert classify_enum_diff_additive(BASE, head) is False


def test_value_change_plus_addition_escalates() -> None:
    """An addition does not launder a value edit made in the same diff."""
    head = _mutate(
        '    PROVIDER_TIMEOUT = "provider_timeout"\n',
        '    PROVIDER_TIMEOUT = "timeout"\n    AUTH_FAILED = "auth_failed"\n',
    )
    assert classify_enum_diff_additive(BASE, head) is False


def test_method_body_change_escalates() -> None:
    """Non-member edits are structure; behaviour can change without any member."""
    head = _mutate(
        "return self is EnumTerminalFailureCause.PROVIDER_TIMEOUT",
        "return True",
    )
    assert classify_enum_diff_additive(BASE, head) is False


def test_new_method_escalates() -> None:
    head = _mutate(
        "    def is_retryable(self) -> bool:",
        "    def is_fatal(self) -> bool:\n        return True\n\n"
        "    def is_retryable(self) -> bool:",
    )
    assert classify_enum_diff_additive(BASE, head) is False


def test_base_class_change_escalates() -> None:
    head = _mutate("(StrEnum)", "(str, Enum)")
    assert classify_enum_diff_additive(BASE, head) is False


def test_import_change_escalates() -> None:
    head = _mutate("from enum import StrEnum", "from enum import Enum, StrEnum")
    assert classify_enum_diff_additive(BASE, head) is False


def test_class_removal_escalates() -> None:
    head = "from enum import StrEnum\n"
    assert classify_enum_diff_additive(BASE, head) is False


def test_file_deletion_escalates() -> None:
    assert classify_enum_diff_additive(BASE, None) is False


@pytest.mark.parametrize("broken", ["class Enum(:\n", "    return 1\n", "'"])
def test_unparseable_head_escalates(broken: str) -> None:
    assert classify_enum_diff_additive(BASE, broken) is False


@pytest.mark.parametrize("broken", ["class Enum(:\n", "def (\n"])
def test_unparseable_base_escalates(broken: str) -> None:
    """A base we cannot parse cannot be proven a subset of head."""
    assert classify_enum_diff_additive(broken, BASE) is False


def test_both_none_escalates() -> None:
    assert classify_enum_diff_additive(None, None) is False


# --- shape helper ---------------------------------------------------------


def test_shape_separates_members_from_structure() -> None:
    shape = enum_module_shape(BASE)
    assert shape is not None
    assert shape.members == {
        "EnumTerminalFailureCause.PROVIDER_QUOTA_EXHAUSTED": "'provider_quota_exhausted'",
        "EnumTerminalFailureCause.PROVIDER_TIMEOUT": "'provider_timeout'",
    }
    # Members are stripped from the structural fingerprint, the method is not.
    assert "provider_timeout" not in shape.structure
    assert "is_retryable" in shape.structure


def test_shape_returns_none_on_syntax_error() -> None:
    assert enum_module_shape("class (:") is None


def test_underscore_names_are_structure_not_members() -> None:
    """``_ignore_``/``_order_`` are enum machinery — editing them must escalate."""
    source = "from enum import StrEnum\n\n\nclass E(StrEnum):\n    _order_ = 'A'\n    A = 'a'\n"
    shape = enum_module_shape(source)
    assert shape is not None
    assert set(shape.members) == {"E.A"}
    assert "_order_" in shape.structure
