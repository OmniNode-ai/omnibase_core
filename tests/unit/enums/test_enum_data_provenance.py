# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumDataProvenance."""

import pytest

from omnibase_core.enums.enum_data_provenance import EnumDataProvenance


@pytest.mark.unit
def test_member_count() -> None:
    assert len(EnumDataProvenance) == 5


@pytest.mark.unit
@pytest.mark.parametrize(
    ("member", "value"),
    [
        (EnumDataProvenance.DEMO_SEEDED, "demo_seeded"),
        (EnumDataProvenance.DEMO_PROJECTED_SHORTCUT, "demo_projected_shortcut"),
        (EnumDataProvenance.MEASURED, "measured"),
        (EnumDataProvenance.ESTIMATED, "estimated"),
        (EnumDataProvenance.UNKNOWN, "unknown"),
    ],
)
def test_member_values(member: EnumDataProvenance, value: str) -> None:
    assert member == value
    assert member.value == value


@pytest.mark.unit
def test_no_implicit_aliases() -> None:
    with pytest.raises(ValueError):
        EnumDataProvenance("not_a_real_value")


@pytest.mark.unit
def test_missing_returns_none_then_raises() -> None:
    assert EnumDataProvenance._missing_("bogus") is None


@pytest.mark.unit
def test_canonical_lookup() -> None:
    assert EnumDataProvenance("measured") is EnumDataProvenance.MEASURED
    assert EnumDataProvenance("unknown") is EnumDataProvenance.UNKNOWN
