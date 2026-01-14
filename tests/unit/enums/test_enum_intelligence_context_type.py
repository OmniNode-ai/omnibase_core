"""
Tests for EnumIntelligenceContextType enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_intelligence_context_type import (
    EnumIntelligenceContextType,
)


@pytest.mark.unit
class TestEnumIntelligenceContextType:
    """Test cases for EnumIntelligenceContextType enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        # Discovery contexts
        assert EnumIntelligenceContextType.DISCOVERY_PATTERN == "discovery_pattern"
        assert EnumIntelligenceContextType.DISCOVERY_SOLUTION == "discovery_solution"
        assert EnumIntelligenceContextType.DISCOVERY_ISSUE == "discovery_issue"

        # Problem analysis contexts
        assert EnumIntelligenceContextType.PROBLEM_DIAGNOSIS == "problem_diagnosis"
        assert EnumIntelligenceContextType.PROBLEM_ROOT_CAUSE == "problem_root_cause"
        assert EnumIntelligenceContextType.PROBLEM_WORKAROUND == "problem_workaround"

        # Solution contexts
        assert (
            EnumIntelligenceContextType.SOLUTION_IMPLEMENTATION
            == "solution_implementation"
        )
        assert (
            EnumIntelligenceContextType.SOLUTION_OPTIMIZATION == "solution_optimization"
        )
        assert EnumIntelligenceContextType.SOLUTION_VALIDATION == "solution_validation"

        # Warning contexts
        assert EnumIntelligenceContextType.WARNING_SECURITY == "warning_security"
        assert EnumIntelligenceContextType.WARNING_PERFORMANCE == "warning_performance"
        assert (
            EnumIntelligenceContextType.WARNING_COMPATIBILITY == "warning_compatibility"
        )

        # Coordination contexts
        assert (
            EnumIntelligenceContextType.COORDINATION_REQUEST == "coordination_request"
        )
        assert EnumIntelligenceContextType.COORDINATION_STATUS == "coordination_status"
        assert (
            EnumIntelligenceContextType.COORDINATION_HANDOFF == "coordination_handoff"
        )

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumIntelligenceContextType, str)
        assert issubclass(EnumIntelligenceContextType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values (str() returns value due to StrValueHelper mixin)."""
        assert str(EnumIntelligenceContextType.DISCOVERY_PATTERN) == "discovery_pattern"
        assert str(EnumIntelligenceContextType.PROBLEM_DIAGNOSIS) == "problem_diagnosis"
        assert (
            str(EnumIntelligenceContextType.SOLUTION_IMPLEMENTATION)
            == "solution_implementation"
        )
        assert str(EnumIntelligenceContextType.WARNING_SECURITY) == "warning_security"
        assert (
            str(EnumIntelligenceContextType.COORDINATION_REQUEST)
            == "coordination_request"
        )

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumIntelligenceContextType)
        assert len(values) == 15
        assert EnumIntelligenceContextType.DISCOVERY_PATTERN in values
        assert EnumIntelligenceContextType.PROBLEM_DIAGNOSIS in values
        assert EnumIntelligenceContextType.SOLUTION_IMPLEMENTATION in values
        assert EnumIntelligenceContextType.WARNING_SECURITY in values
        assert EnumIntelligenceContextType.COORDINATION_REQUEST in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert "discovery_pattern" in EnumIntelligenceContextType
        assert "problem_diagnosis" in EnumIntelligenceContextType
        assert "solution_implementation" in EnumIntelligenceContextType
        assert "warning_security" in EnumIntelligenceContextType
        assert "coordination_request" in EnumIntelligenceContextType
        assert "invalid" not in EnumIntelligenceContextType

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumIntelligenceContextType.DISCOVERY_PATTERN == "discovery_pattern"
        assert EnumIntelligenceContextType.PROBLEM_DIAGNOSIS == "problem_diagnosis"
        assert (
            EnumIntelligenceContextType.SOLUTION_IMPLEMENTATION
            == "solution_implementation"
        )
        assert EnumIntelligenceContextType.WARNING_SECURITY == "warning_security"
        assert (
            EnumIntelligenceContextType.COORDINATION_REQUEST == "coordination_request"
        )

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert (
            EnumIntelligenceContextType.DISCOVERY_PATTERN.value == "discovery_pattern"
        )
        assert (
            EnumIntelligenceContextType.PROBLEM_DIAGNOSIS.value == "problem_diagnosis"
        )
        assert (
            EnumIntelligenceContextType.SOLUTION_IMPLEMENTATION.value
            == "solution_implementation"
        )
        assert EnumIntelligenceContextType.WARNING_SECURITY.value == "warning_security"
        assert (
            EnumIntelligenceContextType.COORDINATION_REQUEST.value
            == "coordination_request"
        )

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert (
            EnumIntelligenceContextType("discovery_pattern")
            == EnumIntelligenceContextType.DISCOVERY_PATTERN
        )
        assert (
            EnumIntelligenceContextType("problem_diagnosis")
            == EnumIntelligenceContextType.PROBLEM_DIAGNOSIS
        )
        assert (
            EnumIntelligenceContextType("solution_implementation")
            == EnumIntelligenceContextType.SOLUTION_IMPLEMENTATION
        )
        assert (
            EnumIntelligenceContextType("warning_security")
            == EnumIntelligenceContextType.WARNING_SECURITY
        )
        assert (
            EnumIntelligenceContextType("coordination_request")
            == EnumIntelligenceContextType.COORDINATION_REQUEST
        )

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumIntelligenceContextType("invalid")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [
            context_type.value for context_type in EnumIntelligenceContextType
        ]
        expected_values = [
            "discovery_pattern",
            "discovery_solution",
            "discovery_issue",
            "problem_diagnosis",
            "problem_root_cause",
            "problem_workaround",
            "solution_implementation",
            "solution_optimization",
            "solution_validation",
            "warning_security",
            "warning_performance",
            "warning_compatibility",
            "coordination_request",
            "coordination_status",
            "coordination_handoff",
        ]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Enum for intelligence context types with security validation"
            in EnumIntelligenceContextType.__doc__
        )

    def test_discovery_contexts(self):
        """Test discovery context types."""
        discovery_contexts = [
            EnumIntelligenceContextType.DISCOVERY_PATTERN,
            EnumIntelligenceContextType.DISCOVERY_SOLUTION,
            EnumIntelligenceContextType.DISCOVERY_ISSUE,
        ]
        for context in discovery_contexts:
            assert context in EnumIntelligenceContextType

    def test_problem_analysis_contexts(self):
        """Test problem analysis context types."""
        problem_contexts = [
            EnumIntelligenceContextType.PROBLEM_DIAGNOSIS,
            EnumIntelligenceContextType.PROBLEM_ROOT_CAUSE,
            EnumIntelligenceContextType.PROBLEM_WORKAROUND,
        ]
        for context in problem_contexts:
            assert context in EnumIntelligenceContextType

    def test_solution_contexts(self):
        """Test solution context types."""
        solution_contexts = [
            EnumIntelligenceContextType.SOLUTION_IMPLEMENTATION,
            EnumIntelligenceContextType.SOLUTION_OPTIMIZATION,
            EnumIntelligenceContextType.SOLUTION_VALIDATION,
        ]
        for context in solution_contexts:
            assert context in EnumIntelligenceContextType

    def test_warning_contexts(self):
        """Test warning context types."""
        warning_contexts = [
            EnumIntelligenceContextType.WARNING_SECURITY,
            EnumIntelligenceContextType.WARNING_PERFORMANCE,
            EnumIntelligenceContextType.WARNING_COMPATIBILITY,
        ]
        for context in warning_contexts:
            assert context in EnumIntelligenceContextType

    def test_coordination_contexts(self):
        """Test coordination context types."""
        coordination_contexts = [
            EnumIntelligenceContextType.COORDINATION_REQUEST,
            EnumIntelligenceContextType.COORDINATION_STATUS,
            EnumIntelligenceContextType.COORDINATION_HANDOFF,
        ]
        for context in coordination_contexts:
            assert context in EnumIntelligenceContextType
