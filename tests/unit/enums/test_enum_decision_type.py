"""Unit tests for EnumDecisionType.

Tests serialization/deserialization and basic enum behavior
for the decision classification type enum.
"""

import copy
import json
import pickle

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
        ("member", "value"),
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
    def test_serialization_roundtrip(
        self, member: EnumDecisionType, value: str
    ) -> None:
        """Test enum serialization/deserialization round-trip."""
        # Serialization: member.value equals expected string
        assert member.value == value
        # Direct string comparison (str subclass)
        assert member == value
        # Deserialization: string value constructs back to member
        assert EnumDecisionType(value) == member

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

    def test_str_method(self) -> None:
        """Test __str__ returns the enum value."""
        # Test representative members
        assert str(EnumDecisionType.MODEL_SELECTION) == "model_selection"
        assert str(EnumDecisionType.ESCALATION) == "escalation"
        assert str(EnumDecisionType.CUSTOM) == "custom"
        # Verify str() equals .value for all members
        for member in EnumDecisionType:
            assert str(member) == member.value

    @pytest.mark.parametrize(
        "value",
        ["model_selection", "tool_selection", "custom", "escalation", "route_choice"],
    )
    def test_is_valid_with_valid_values(self, value: str) -> None:
        """Test is_valid returns True for valid enum values."""
        assert EnumDecisionType.is_valid(value) is True

    @pytest.mark.parametrize(
        "value",
        ["invalid_type", "", "MODEL_SELECTION", "ModelSelection", "decision"],
    )
    def test_is_valid_with_invalid_values(self, value: str) -> None:
        """Test is_valid returns False for invalid values."""
        assert EnumDecisionType.is_valid(value) is False

    @pytest.mark.parametrize(
        ("member", "expected"),
        [
            (EnumDecisionType.ESCALATION, True),
            (EnumDecisionType.EARLY_TERMINATION, True),
            (EnumDecisionType.MODEL_SELECTION, False),
            (EnumDecisionType.TOOL_SELECTION, False),
            (EnumDecisionType.ROUTE_CHOICE, False),
            (EnumDecisionType.RETRY_STRATEGY, False),
            (EnumDecisionType.PARAMETER_CHOICE, False),
            (EnumDecisionType.CUSTOM, False),
        ],
    )
    def test_is_terminal_decision(
        self, member: EnumDecisionType, expected: bool
    ) -> None:
        """Test is_terminal_decision identifies workflow-ending decisions."""
        assert member.is_terminal_decision() is expected

    @pytest.mark.parametrize(
        ("member", "expected"),
        [
            (EnumDecisionType.MODEL_SELECTION, True),
            (EnumDecisionType.TOOL_SELECTION, True),
            (EnumDecisionType.ROUTE_CHOICE, True),
            (EnumDecisionType.PARAMETER_CHOICE, True),
            (EnumDecisionType.ESCALATION, False),
            (EnumDecisionType.EARLY_TERMINATION, False),
            (EnumDecisionType.RETRY_STRATEGY, False),
            (EnumDecisionType.CUSTOM, False),
        ],
    )
    def test_is_selection_decision(
        self, member: EnumDecisionType, expected: bool
    ) -> None:
        """Test is_selection_decision identifies selection-type decisions."""
        assert member.is_selection_decision() is expected

    @pytest.mark.parametrize("member", list(EnumDecisionType))
    def test_pickle_serialization(self, member: EnumDecisionType) -> None:
        """Test enum values can be pickled and unpickled correctly."""
        pickled = pickle.dumps(member)
        unpickled = pickle.loads(pickled)
        # Verify identity and equality
        assert unpickled == member
        assert unpickled is member  # Enum identity preserved
        assert unpickled.value == member.value

    @pytest.mark.parametrize("member", list(EnumDecisionType))
    def test_deep_copy(self, member: EnumDecisionType) -> None:
        """Test enum values can be deep copied correctly."""
        copied = copy.deepcopy(member)
        # Verify identity and equality
        assert copied == member
        assert copied is member  # Enum identity preserved
        assert copied.value == member.value
