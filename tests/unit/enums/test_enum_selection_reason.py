# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumSelectionReason enum (OMN-12843 / M3 Context Authority Rule).

EnumSelectionReason is the typed authority enum stamped on every selected
context factor so that per-run injection is auditable. It encodes WHY a factor
was selected: by measured effectiveness, by required-factor policy, by an
experiment arm, by exploration, or as an explicit no-score fallback.
"""

import json
from enum import Enum, StrEnum

import pytest

from omnibase_core.enums.enum_selection_reason import EnumSelectionReason


@pytest.mark.unit
class TestEnumSelectionReason:
    """Test cases for EnumSelectionReason enum."""

    def test_all_reasons_exist(self) -> None:
        """Verify the exact set of selection reasons required by the plan."""
        assert EnumSelectionReason.POLICY_EFFECTIVENESS == "policy_effectiveness"
        assert EnumSelectionReason.POLICY_REQUIRED_FACTOR == "policy_required_factor"
        assert EnumSelectionReason.EXPERIMENT_ASSIGNMENT == "experiment_assignment"
        assert EnumSelectionReason.EXPLORATION == "exploration"
        assert EnumSelectionReason.FALLBACK_NO_SCORE == "fallback_no_score"

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from StrEnum (and therefore str + Enum)."""
        assert issubclass(EnumSelectionReason, StrEnum)
        assert issubclass(EnumSelectionReason, str)
        assert issubclass(EnumSelectionReason, Enum)

    def test_exactly_five_members(self) -> None:
        """Plan mandates exactly five reasons — no more, no fewer."""
        values = {member.value for member in EnumSelectionReason}
        assert values == {
            "policy_effectiveness",
            "policy_required_factor",
            "experiment_assignment",
            "exploration",
            "fallback_no_score",
        }
        assert len(list(EnumSelectionReason)) == 5

    def test_json_serialization(self) -> None:
        """Test that enum values can be JSON serialized as their string value."""
        assert json.dumps(EnumSelectionReason.POLICY_EFFECTIVENESS) == (
            '"policy_effectiveness"'
        )

    def test_enum_creation_from_string(self) -> None:
        """Test that enum can be constructed from its string value."""
        assert (
            EnumSelectionReason("experiment_assignment")
            == EnumSelectionReason.EXPERIMENT_ASSIGNMENT
        )

    def test_invalid_value_raises_error(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumSelectionReason("not_a_reason")

    def test_values_are_unique(self) -> None:
        """Test that enum values are unique."""
        values = [member.value for member in EnumSelectionReason]
        assert len(values) == len(set(values))
