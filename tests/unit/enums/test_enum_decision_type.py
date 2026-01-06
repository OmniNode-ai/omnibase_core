"""Unit tests for EnumDecisionType.

Tests serialization/deserialization and basic enum behavior
for the decision classification type enum.
"""

import json

import pytest

from omnibase_core.enums.enum_decision_type import EnumDecisionType


@pytest.mark.unit
class TestEnumDecisionType:
    """Tests for EnumDecisionType enum."""

    def test_all_values_defined(self) -> None:
        """Verify all 8 expected decision types are defined."""
        expected_values = {
            "model_selection",
            "route_choice",
            "retry_strategy",
            "tool_selection",
            "escalation",
            "early_termination",
            "parameter_choice",
            "custom",
        }
        actual_values = {member.value for member in EnumDecisionType}
        assert actual_values == expected_values
        assert len(EnumDecisionType) == 8

    def test_string_enum_inheritance(self) -> None:
        """Verify enum inherits from str for JSON serialization."""
        assert isinstance(EnumDecisionType.MODEL_SELECTION, str)
        assert EnumDecisionType.MODEL_SELECTION == "model_selection"

    @pytest.mark.parametrize(
        ("member", "expected_value"),
        [
            (EnumDecisionType.MODEL_SELECTION, "model_selection"),
            (EnumDecisionType.ROUTE_CHOICE, "route_choice"),
            (EnumDecisionType.RETRY_STRATEGY, "retry_strategy"),
            (EnumDecisionType.TOOL_SELECTION, "tool_selection"),
            (EnumDecisionType.ESCALATION, "escalation"),
            (EnumDecisionType.EARLY_TERMINATION, "early_termination"),
            (EnumDecisionType.PARAMETER_CHOICE, "parameter_choice"),
            (EnumDecisionType.CUSTOM, "custom"),
        ],
    )
    def test_serialization(self, member: EnumDecisionType, expected_value: str) -> None:
        """Test enum serializes to expected string value."""
        assert member.value == expected_value

    @pytest.mark.parametrize(
        "value",
        [
            "model_selection",
            "route_choice",
            "retry_strategy",
            "tool_selection",
            "escalation",
            "early_termination",
            "parameter_choice",
            "custom",
        ],
    )
    def test_deserialization(self, value: str) -> None:
        """Test enum deserializes from string value."""
        result = EnumDecisionType(value)
        assert result.value == value

    def test_invalid_value_raises(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumDecisionType("invalid_decision")

    def test_json_serialization(self) -> None:
        """Test JSON serialization/deserialization."""
        data = {"decision_type": EnumDecisionType.TOOL_SELECTION}
        json_str = json.dumps(data)
        assert '"tool_selection"' in json_str

        # Deserialize
        parsed = json.loads(json_str)
        result = EnumDecisionType(parsed["decision_type"])
        assert result == EnumDecisionType.TOOL_SELECTION

    def test_custom_escape_hatch(self) -> None:
        """Test CUSTOM value exists as forward-compatibility escape hatch."""
        assert EnumDecisionType.CUSTOM.value == "custom"
        # Can be used directly
        custom = EnumDecisionType("custom")
        assert custom == EnumDecisionType.CUSTOM

    def test_hashable(self) -> None:
        """Test enum values are hashable for use in sets/dicts."""
        decision_set = {
            EnumDecisionType.MODEL_SELECTION,
            EnumDecisionType.TOOL_SELECTION,
        }
        assert len(decision_set) == 2
        assert EnumDecisionType.MODEL_SELECTION in decision_set

    def test_equality(self) -> None:
        """Test enum equality comparisons."""
        assert EnumDecisionType.MODEL_SELECTION == EnumDecisionType.MODEL_SELECTION
        assert EnumDecisionType.MODEL_SELECTION == "model_selection"
        assert EnumDecisionType.MODEL_SELECTION != EnumDecisionType.TOOL_SELECTION
