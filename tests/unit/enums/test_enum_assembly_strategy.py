"""
Tests for EnumAssemblyStrategy enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_assembly_strategy import EnumAssemblyStrategy


@pytest.mark.unit
class TestEnumAssemblyStrategy:
    """Test cases for EnumAssemblyStrategy enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumAssemblyStrategy.CONCATENATE == "concatenate"
        assert EnumAssemblyStrategy.STRUCTURED_MERGE == "structured_merge"
        assert EnumAssemblyStrategy.WEIGHTED_CONSENSUS == "weighted_consensus"
        assert EnumAssemblyStrategy.BEST_OF_N == "best_of_n"
        assert EnumAssemblyStrategy.COMPARATIVE_ANALYSIS == "comparative_analysis"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumAssemblyStrategy, str)
        assert issubclass(EnumAssemblyStrategy, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        strategy = EnumAssemblyStrategy.CONCATENATE
        assert isinstance(strategy, str)
        assert strategy == "concatenate"
        assert len(strategy) == 11
        assert strategy.startswith("concat")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumAssemblyStrategy)
        assert len(values) == 5
        assert EnumAssemblyStrategy.CONCATENATE in values
        assert EnumAssemblyStrategy.COMPARATIVE_ANALYSIS in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "concatenate" in EnumAssemblyStrategy
        assert "invalid_strategy" not in EnumAssemblyStrategy

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        strategy1 = EnumAssemblyStrategy.CONCATENATE
        strategy2 = EnumAssemblyStrategy.STRUCTURED_MERGE

        assert strategy1 != strategy2
        assert strategy1 == "concatenate"
        assert strategy2 == "structured_merge"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        strategy = EnumAssemblyStrategy.WEIGHTED_CONSENSUS
        serialized = strategy.value
        assert serialized == "weighted_consensus"

        # Test JSON serialization
        import json

        json_str = json.dumps(strategy)
        assert json_str == '"weighted_consensus"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        strategy = EnumAssemblyStrategy("best_of_n")
        assert strategy == EnumAssemblyStrategy.BEST_OF_N

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumAssemblyStrategy("invalid_strategy")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "concatenate",
            "structured_merge",
            "weighted_consensus",
            "best_of_n",
            "comparative_analysis",
        }

        actual_values = {member.value for member in EnumAssemblyStrategy}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "LLM result assembly strategies" in EnumAssemblyStrategy.__doc__

    def test_enum_assembly_strategies(self):
        """Test that enum covers typical assembly strategies."""
        # Test basic strategies
        assert EnumAssemblyStrategy.CONCATENATE in EnumAssemblyStrategy
        assert EnumAssemblyStrategy.STRUCTURED_MERGE in EnumAssemblyStrategy

        # Test advanced strategies
        assert EnumAssemblyStrategy.WEIGHTED_CONSENSUS in EnumAssemblyStrategy
        assert EnumAssemblyStrategy.BEST_OF_N in EnumAssemblyStrategy
        assert EnumAssemblyStrategy.COMPARATIVE_ANALYSIS in EnumAssemblyStrategy
