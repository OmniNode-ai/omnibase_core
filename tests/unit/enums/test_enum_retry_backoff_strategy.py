"""
Unit tests for EnumRetryBackoffStrategy.

Tests all aspects of the retry backoff strategy enum including:
- Enum value validation
- String representation
- JSON serialization compatibility
- Pydantic integration
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_retry_backoff_strategy import EnumRetryBackoffStrategy


@pytest.mark.unit
class TestEnumRetryBackoffStrategy:
    """Test cases for EnumRetryBackoffStrategy."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "FIXED": "fixed",
            "LINEAR": "linear",
            "EXPONENTIAL": "exponential",
            "RANDOM": "random",
            "FIBONACCI": "fibonacci",
        }

        for name, value in expected_values.items():
            strategy = getattr(EnumRetryBackoffStrategy, name)
            assert strategy.value == value
            assert str(strategy) == value

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumRetryBackoffStrategy.FIXED) == "fixed"
        assert str(EnumRetryBackoffStrategy.LINEAR) == "linear"
        assert str(EnumRetryBackoffStrategy.EXPONENTIAL) == "exponential"
        assert str(EnumRetryBackoffStrategy.RANDOM) == "random"
        assert str(EnumRetryBackoffStrategy.FIBONACCI) == "fibonacci"

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        assert EnumRetryBackoffStrategy.FIXED == EnumRetryBackoffStrategy.FIXED
        assert EnumRetryBackoffStrategy.FIXED != EnumRetryBackoffStrategy.LINEAR
        assert EnumRetryBackoffStrategy.EXPONENTIAL == "exponential"
        assert EnumRetryBackoffStrategy.RANDOM != "fixed"

    def test_enum_membership(self):
        """Test enum membership checks."""
        assert EnumRetryBackoffStrategy.FIXED in EnumRetryBackoffStrategy
        assert EnumRetryBackoffStrategy.LINEAR in EnumRetryBackoffStrategy
        assert EnumRetryBackoffStrategy.EXPONENTIAL in EnumRetryBackoffStrategy

    def test_enum_iteration(self):
        """Test iteration over enum values."""
        strategies = list(EnumRetryBackoffStrategy)
        assert len(strategies) == 5
        assert EnumRetryBackoffStrategy.FIXED in strategies
        assert EnumRetryBackoffStrategy.LINEAR in strategies
        assert EnumRetryBackoffStrategy.EXPONENTIAL in strategies
        assert EnumRetryBackoffStrategy.RANDOM in strategies
        assert EnumRetryBackoffStrategy.FIBONACCI in strategies

    def test_json_serialization(self):
        """Test JSON serialization of enum values."""
        assert json.dumps(EnumRetryBackoffStrategy.FIXED) == '"fixed"'
        assert json.dumps(EnumRetryBackoffStrategy.EXPONENTIAL) == '"exponential"'

    def test_pydantic_model_integration(self):
        """Test Pydantic model integration with enum."""

        class RetryConfig(BaseModel):
            strategy: EnumRetryBackoffStrategy

        # Test valid enum value
        config = RetryConfig(strategy=EnumRetryBackoffStrategy.EXPONENTIAL)
        assert config.strategy == EnumRetryBackoffStrategy.EXPONENTIAL

        # Test valid string value
        config = RetryConfig(strategy="linear")
        assert config.strategy == EnumRetryBackoffStrategy.LINEAR

        # Test invalid value
        with pytest.raises(ValidationError):
            RetryConfig(strategy="invalid_strategy")

    def test_pydantic_serialization(self):
        """Test Pydantic serialization of enum values."""

        class RetryConfig(BaseModel):
            strategy: EnumRetryBackoffStrategy

        config = RetryConfig(strategy=EnumRetryBackoffStrategy.FIBONACCI)

        # Test model_dump
        dumped = config.model_dump()
        assert dumped["strategy"] == "fibonacci"

        # Test model_dump_json
        json_str = config.model_dump_json()
        assert '"strategy":"fibonacci"' in json_str

    def test_enum_uniqueness(self):
        """Test that all enum values are unique."""
        values = [strategy.value for strategy in EnumRetryBackoffStrategy]
        assert len(values) == len(set(values))

    def test_enum_value_access(self):
        """Test direct value access."""
        assert EnumRetryBackoffStrategy.FIXED.value == "fixed"
        assert EnumRetryBackoffStrategy.LINEAR.value == "linear"
        assert EnumRetryBackoffStrategy.EXPONENTIAL.value == "exponential"

    def test_enum_name_access(self):
        """Test enum name access."""
        assert EnumRetryBackoffStrategy.FIXED.name == "FIXED"
        assert EnumRetryBackoffStrategy.LINEAR.name == "LINEAR"
        assert EnumRetryBackoffStrategy.EXPONENTIAL.name == "EXPONENTIAL"

    def test_string_coercion(self):
        """Test that enum can be used as string."""
        strategy = EnumRetryBackoffStrategy.EXPONENTIAL
        assert f"Using {strategy} backoff" == "Using exponential backoff"

    def test_enum_hashing(self):
        """Test that enum values are hashable."""
        strategy_set = {
            EnumRetryBackoffStrategy.FIXED,
            EnumRetryBackoffStrategy.LINEAR,
            EnumRetryBackoffStrategy.EXPONENTIAL,
        }
        assert len(strategy_set) == 3
        assert EnumRetryBackoffStrategy.FIXED in strategy_set

    def test_enum_repr(self):
        """Test enum representation."""
        assert repr(EnumRetryBackoffStrategy.FIXED).startswith(
            "<EnumRetryBackoffStrategy"
        )
        assert "fixed" in repr(EnumRetryBackoffStrategy.FIXED)


@pytest.mark.unit
class TestEnumRetryBackoffStrategyEdgeCases:
    """Test edge cases for EnumRetryBackoffStrategy."""

    def test_case_sensitivity(self):
        """Test that enum values are case-sensitive."""

        class RetryConfig(BaseModel):
            strategy: EnumRetryBackoffStrategy

        # Lowercase should work
        config = RetryConfig(strategy="fixed")
        assert config.strategy == EnumRetryBackoffStrategy.FIXED

        # Uppercase should fail
        with pytest.raises(ValidationError):
            RetryConfig(strategy="FIXED")

        # Mixed case should fail
        with pytest.raises(ValidationError):
            RetryConfig(strategy="Fixed")

    def test_whitespace_handling(self):
        """Test that whitespace in values is rejected."""

        class RetryConfig(BaseModel):
            strategy: EnumRetryBackoffStrategy

        with pytest.raises(ValidationError):
            RetryConfig(strategy=" fixed")

        with pytest.raises(ValidationError):
            RetryConfig(strategy="fixed ")

        with pytest.raises(ValidationError):
            RetryConfig(strategy="fixed ")

    def test_empty_string(self):
        """Test that empty string is rejected."""

        class RetryConfig(BaseModel):
            strategy: EnumRetryBackoffStrategy

        with pytest.raises(ValidationError):
            RetryConfig(strategy="")

    def test_none_value(self):
        """Test that None is rejected."""

        class RetryConfig(BaseModel):
            strategy: EnumRetryBackoffStrategy

        with pytest.raises(ValidationError):
            RetryConfig(strategy=None)
