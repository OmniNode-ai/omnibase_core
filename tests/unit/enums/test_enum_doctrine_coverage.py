# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumDoctrineCoverage."""

import pytest

from omnibase_core.enums.enum_doctrine_coverage import EnumDoctrineCoverage


@pytest.mark.unit
def test_member_count() -> None:
    assert len(EnumDoctrineCoverage) == 3


@pytest.mark.unit
@pytest.mark.parametrize(
    ("member", "value"),
    [
        (EnumDoctrineCoverage.UNCOVERED, "uncovered"),
        (EnumDoctrineCoverage.ADVISORY, "advisory"),
        (EnumDoctrineCoverage.ENFORCED, "enforced"),
    ],
)
def test_member_values(member: EnumDoctrineCoverage, value: str) -> None:
    assert member == value
    assert member.value == value


@pytest.mark.unit
def test_no_implicit_aliases() -> None:
    with pytest.raises(ValueError):
        EnumDoctrineCoverage("not_a_real_value")


@pytest.mark.unit
def test_missing_returns_none_then_raises() -> None:
    assert EnumDoctrineCoverage._missing_("bogus") is None


@pytest.mark.unit
def test_canonical_lookup() -> None:
    assert EnumDoctrineCoverage("uncovered") is EnumDoctrineCoverage.UNCOVERED
    assert EnumDoctrineCoverage("enforced") is EnumDoctrineCoverage.ENFORCED
