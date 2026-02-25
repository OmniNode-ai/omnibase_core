# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for EnumDecisionType extensions (OMN-2763).

Tests the five new values added to EnumDecisionType:
- TECH_STACK_CHOICE, DESIGN_PATTERN, API_CONTRACT, SCOPE_BOUNDARY, REQUIREMENT_CHOICE

Verifies:
- All five values exist and have correct string representations
- is_selection_decision() returns True for all five new values
- is_terminal_decision() returns False for all five new values
- is_valid() returns True for each new value's string
- Existing behaviour of original values is unaffected
"""

import pytest

pytestmark = pytest.mark.unit

from omnibase_core.enums.enum_decision_type import EnumDecisionType

# ============================================================================
# New enum values existence and string values
# ============================================================================


class TestNewEnumValues:
    """Tests for the five new EnumDecisionType values."""

    def test_tech_stack_choice_value(self) -> None:
        assert EnumDecisionType.TECH_STACK_CHOICE.value == "tech_stack_choice"

    def test_design_pattern_value(self) -> None:
        assert EnumDecisionType.DESIGN_PATTERN.value == "design_pattern"

    def test_api_contract_value(self) -> None:
        assert EnumDecisionType.API_CONTRACT.value == "api_contract"

    def test_scope_boundary_value(self) -> None:
        assert EnumDecisionType.SCOPE_BOUNDARY.value == "scope_boundary"

    def test_requirement_choice_value(self) -> None:
        assert EnumDecisionType.REQUIREMENT_CHOICE.value == "requirement_choice"


# ============================================================================
# is_selection_decision for new values
# ============================================================================


class TestIsSelectionDecision:
    """Tests for is_selection_decision() including new values."""

    @pytest.mark.parametrize(
        "decision_type",
        [
            EnumDecisionType.TECH_STACK_CHOICE,
            EnumDecisionType.DESIGN_PATTERN,
            EnumDecisionType.API_CONTRACT,
            EnumDecisionType.SCOPE_BOUNDARY,
            EnumDecisionType.REQUIREMENT_CHOICE,
        ],
    )
    def test_new_values_are_selection_decisions(
        self, decision_type: EnumDecisionType
    ) -> None:
        assert decision_type.is_selection_decision() is True

    def test_original_selection_decisions_unchanged(self) -> None:
        """Verify original selection decisions still return True."""
        assert EnumDecisionType.MODEL_SELECTION.is_selection_decision() is True
        assert EnumDecisionType.MODEL_SELECT.is_selection_decision() is True
        assert EnumDecisionType.PARAMETER_CHOICE.is_selection_decision() is True
        assert EnumDecisionType.ROUTE_CHOICE.is_selection_decision() is True
        assert EnumDecisionType.WORKFLOW_ROUTE.is_selection_decision() is True
        assert EnumDecisionType.TOOL_SELECTION.is_selection_decision() is True
        assert EnumDecisionType.TOOL_PICK.is_selection_decision() is True

    def test_non_selection_decisions_unchanged(self) -> None:
        """Verify non-selection decisions still return False."""
        assert EnumDecisionType.ESCALATION.is_selection_decision() is False
        assert EnumDecisionType.EARLY_TERMINATION.is_selection_decision() is False
        assert EnumDecisionType.RETRY_STRATEGY.is_selection_decision() is False
        assert EnumDecisionType.CUSTOM.is_selection_decision() is False


# ============================================================================
# is_terminal_decision for new values
# ============================================================================


class TestIsTerminalDecision:
    """Tests that new values are not terminal decisions."""

    @pytest.mark.parametrize(
        "decision_type",
        [
            EnumDecisionType.TECH_STACK_CHOICE,
            EnumDecisionType.DESIGN_PATTERN,
            EnumDecisionType.API_CONTRACT,
            EnumDecisionType.SCOPE_BOUNDARY,
            EnumDecisionType.REQUIREMENT_CHOICE,
        ],
    )
    def test_new_values_not_terminal(self, decision_type: EnumDecisionType) -> None:
        assert decision_type.is_terminal_decision() is False


# ============================================================================
# is_valid for new values
# ============================================================================


class TestIsValid:
    """Tests for is_valid() with new value strings."""

    @pytest.mark.parametrize(
        "value",
        [
            "tech_stack_choice",
            "design_pattern",
            "api_contract",
            "scope_boundary",
            "requirement_choice",
        ],
    )
    def test_new_value_strings_are_valid(self, value: str) -> None:
        assert EnumDecisionType.is_valid(value) is True

    def test_invalid_string_still_invalid(self) -> None:
        assert EnumDecisionType.is_valid("not_a_real_decision_type") is False


# ============================================================================
# String coercion (Pydantic compatibility)
# ============================================================================


class TestStringCoercion:
    """Tests that new values work with string coercion in Pydantic models."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("tech_stack_choice", EnumDecisionType.TECH_STACK_CHOICE),
            ("design_pattern", EnumDecisionType.DESIGN_PATTERN),
            ("api_contract", EnumDecisionType.API_CONTRACT),
            ("scope_boundary", EnumDecisionType.SCOPE_BOUNDARY),
            ("requirement_choice", EnumDecisionType.REQUIREMENT_CHOICE),
        ],
    )
    def test_string_resolves_to_enum_member(
        self, value: str, expected: EnumDecisionType
    ) -> None:
        resolved = EnumDecisionType(value)
        assert resolved is expected
