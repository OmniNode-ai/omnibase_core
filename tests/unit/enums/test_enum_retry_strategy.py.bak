"""Tests for EnumRetryStrategy."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_retry_strategy import EnumRetryStrategy


class TestEnumRetryStrategy:
    """Test suite for EnumRetryStrategy."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumRetryStrategy.NONE == "none"
        assert EnumRetryStrategy.IMMEDIATE == "immediate"
        assert EnumRetryStrategy.LINEAR_BACKOFF == "linear_backoff"
        assert EnumRetryStrategy.EXPONENTIAL_BACKOFF == "exponential_backoff"
        assert EnumRetryStrategy.CIRCUIT_BREAKER == "circuit_breaker"
        assert EnumRetryStrategy.MANUAL_INTERVENTION == "manual_intervention"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumRetryStrategy, str)
        assert issubclass(EnumRetryStrategy, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        strategy = EnumRetryStrategy.IMMEDIATE
        assert isinstance(strategy, str)
        assert strategy == "immediate"
        assert len(strategy) == 9

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumRetryStrategy)
        assert len(values) == 6
        assert EnumRetryStrategy.NONE in values
        assert EnumRetryStrategy.MANUAL_INTERVENTION in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumRetryStrategy.EXPONENTIAL_BACKOFF in EnumRetryStrategy
        assert "exponential_backoff" in [e.value for e in EnumRetryStrategy]

    def test_enum_comparison(self):
        """Test enum comparison."""
        strategy1 = EnumRetryStrategy.LINEAR_BACKOFF
        strategy2 = EnumRetryStrategy.LINEAR_BACKOFF
        strategy3 = EnumRetryStrategy.CIRCUIT_BREAKER

        assert strategy1 == strategy2
        assert strategy1 != strategy3
        assert strategy1 == "linear_backoff"

    def test_enum_serialization(self):
        """Test enum serialization."""
        strategy = EnumRetryStrategy.CIRCUIT_BREAKER
        serialized = strategy.value
        assert serialized == "circuit_breaker"
        json_str = json.dumps(strategy)
        assert json_str == '"circuit_breaker"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        strategy = EnumRetryStrategy("immediate")
        assert strategy == EnumRetryStrategy.IMMEDIATE

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumRetryStrategy("invalid_strategy")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "none",
            "immediate",
            "linear_backoff",
            "exponential_backoff",
            "circuit_breaker",
            "manual_intervention",
        }
        actual_values = {e.value for e in EnumRetryStrategy}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumRetryStrategy.__doc__ is not None
        assert "retry" in EnumRetryStrategy.__doc__.lower()

    def test_no_retry_strategies(self):
        """Test no-retry strategy group."""
        no_retry = {
            EnumRetryStrategy.NONE,
            EnumRetryStrategy.MANUAL_INTERVENTION,
        }
        assert all(s in EnumRetryStrategy for s in no_retry)

    def test_automatic_retry_strategies(self):
        """Test automatic retry strategy group."""
        automatic_retry = {
            EnumRetryStrategy.IMMEDIATE,
            EnumRetryStrategy.LINEAR_BACKOFF,
            EnumRetryStrategy.EXPONENTIAL_BACKOFF,
        }
        assert all(s in EnumRetryStrategy for s in automatic_retry)

    def test_advanced_strategies(self):
        """Test advanced retry strategies."""
        advanced = {EnumRetryStrategy.CIRCUIT_BREAKER}
        assert all(s in EnumRetryStrategy for s in advanced)

    def test_all_strategies_categorized(self):
        """Test that all strategies are properly categorized."""
        # No automatic retry
        no_retry = {
            EnumRetryStrategy.NONE,
            EnumRetryStrategy.MANUAL_INTERVENTION,
        }
        # Automatic retry with backoff
        automatic = {
            EnumRetryStrategy.IMMEDIATE,
            EnumRetryStrategy.LINEAR_BACKOFF,
            EnumRetryStrategy.EXPONENTIAL_BACKOFF,
        }
        # Advanced patterns
        advanced = {EnumRetryStrategy.CIRCUIT_BREAKER}

        all_strategies = no_retry | automatic | advanced
        assert all_strategies == set(EnumRetryStrategy)

    def test_backoff_strategies(self):
        """Test backoff-based strategies."""
        backoff_strategies = {
            EnumRetryStrategy.LINEAR_BACKOFF,
            EnumRetryStrategy.EXPONENTIAL_BACKOFF,
        }
        for strategy in backoff_strategies:
            assert "backoff" in strategy.value
