# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the category-weighted user-correction enums (OMN-12846).

These enums cross the omnibase_core / omnimarket boundary: the typed
user-correction event in omnimarket references them, so they live in core.

The category axis (what kind of correction) is deliberately kept orthogonal
to the failure axis (whether the correction counts against context selection)
— there is no single rolled-up score, by design (anti-flattening invariant).
"""

from enum import StrEnum

import pytest

from omnibase_core.enums.enum_correction_failure_axis import EnumCorrectionFailureAxis
from omnibase_core.enums.enum_user_correction_category import EnumUserCorrectionCategory


@pytest.mark.unit
class TestEnumUserCorrectionCategory:
    """The correction category is a finite, exhaustive, typed set."""

    def test_correction_category_enum_is_exhaustive(self) -> None:
        """Exactly the 7 named members, no more, no fewer."""
        expected = {
            "CLARIFICATION",
            "CONSTRAINT_VIOLATION",
            "SCOPE_REDUCTION",
            "SCOPE_EXPANSION",
            "PRIORITY_SHIFT",
            "STYLE",
            "INTENT",
        }
        actual = {member.name for member in EnumUserCorrectionCategory}
        assert actual == expected

    def test_is_str_enum(self) -> None:
        """Must be a StrEnum for cross-process wire stability."""
        assert issubclass(EnumUserCorrectionCategory, StrEnum)

    def test_enum_prefix(self) -> None:
        """Class name carries the canonical Enum prefix."""
        assert EnumUserCorrectionCategory.__name__.startswith("Enum")

    def test_members_round_trip_by_value(self) -> None:
        """Each member reconstructs from its own string value."""
        for member in EnumUserCorrectionCategory:
            assert EnumUserCorrectionCategory(member.value) is member


@pytest.mark.unit
class TestEnumCorrectionFailureAxis:
    """The failure axis gates whether a correction counts against context."""

    def test_failure_axis_misunderstanding_vs_new_information(self) -> None:
        """Exactly MISUNDERSTANDING and NEW_INFORMATION."""
        expected = {"MISUNDERSTANDING", "NEW_INFORMATION"}
        actual = {member.name for member in EnumCorrectionFailureAxis}
        assert actual == expected

    def test_is_str_enum(self) -> None:
        """Must be a StrEnum for cross-process wire stability."""
        assert issubclass(EnumCorrectionFailureAxis, StrEnum)

    def test_enum_prefix(self) -> None:
        """Class name carries the canonical Enum prefix."""
        assert EnumCorrectionFailureAxis.__name__.startswith("Enum")

    def test_members_round_trip_by_value(self) -> None:
        """Each member reconstructs from its own string value."""
        for member in EnumCorrectionFailureAxis:
            assert EnumCorrectionFailureAxis(member.value) is member
