# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumDegradedBehavior."""

import pytest

from omnibase_core.enums.enum_degraded_behavior import EnumDegradedBehavior


@pytest.mark.unit
def test_member_count() -> None:
    assert len(EnumDegradedBehavior) == 3


@pytest.mark.unit
@pytest.mark.parametrize(
    ("member", "value"),
    [
        (EnumDegradedBehavior.SERVE_STALE_WITH_WARNING, "serve_stale_with_warning"),
        (EnumDegradedBehavior.RETURN_EMPTY, "return_empty"),
        (EnumDegradedBehavior.FAIL_CLOSED, "fail_closed"),
    ],
)
def test_member_values(member: EnumDegradedBehavior, value: str) -> None:
    assert member == value
    assert member.value == value


@pytest.mark.unit
def test_no_implicit_aliases() -> None:
    with pytest.raises(ValueError):
        EnumDegradedBehavior("not_a_real_value")


@pytest.mark.unit
def test_missing_returns_none_then_raises() -> None:
    assert EnumDegradedBehavior._missing_("bogus") is None


@pytest.mark.unit
def test_canonical_lookup() -> None:
    assert EnumDegradedBehavior("return_empty") is EnumDegradedBehavior.RETURN_EMPTY
    assert EnumDegradedBehavior("fail_closed") is EnumDegradedBehavior.FAIL_CLOSED
