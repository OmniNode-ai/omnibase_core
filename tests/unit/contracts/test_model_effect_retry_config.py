"""
Tests for ModelEffectRetryConfig.

Validates retry configuration model including backoff strategies,
circuit breaker patterns, and field validators.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_retry_backoff_strategy import EnumRetryBackoffStrategy
from omnibase_core.models.contracts.model_effect_retry_config import (
    ModelEffectRetryConfig,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError as OnexError


@pytest.mark.unit
class TestModelEffectRetryConfigBasic:
    """Test basic retry configuration functionality."""

    def test_default_configuration(self):
        """Test default retry configuration values."""
        config = ModelEffectRetryConfig()

        assert config.max_attempts == 3
        assert config.backoff_strategy == EnumRetryBackoffStrategy.EXPONENTIAL
        assert config.base_delay_ms == 100
        assert config.max_delay_ms == 5000
        assert config.jitter_enabled is True
        assert config.circuit_breaker_enabled is True
        assert config.circuit_breaker_threshold == 3
        assert config.circuit_breaker_timeout_s == 60

    def test_custom_configuration(self):
        """Test custom retry configuration."""
        config = ModelEffectRetryConfig(
            max_attempts=5,
            backoff_strategy=EnumRetryBackoffStrategy.LINEAR,
            base_delay_ms=200,
            max_delay_ms=10000,
            jitter_enabled=False,
            circuit_breaker_enabled=False,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout_s=120,
        )

        assert config.max_attempts == 5
        assert config.backoff_strategy == EnumRetryBackoffStrategy.LINEAR
        assert config.base_delay_ms == 200
        assert config.max_delay_ms == 10000
        assert config.jitter_enabled is False
        assert config.circuit_breaker_enabled is False
        assert config.circuit_breaker_threshold == 5
        assert config.circuit_breaker_timeout_s == 120

    def test_all_backoff_strategies(self):
        """Test all available backoff strategies."""
        strategies = [
            EnumRetryBackoffStrategy.FIXED,
            EnumRetryBackoffStrategy.LINEAR,
            EnumRetryBackoffStrategy.EXPONENTIAL,
            EnumRetryBackoffStrategy.RANDOM,
            EnumRetryBackoffStrategy.FIBONACCI,
        ]

        for strategy in strategies:
            config = ModelEffectRetryConfig(backoff_strategy=strategy)
            assert config.backoff_strategy == strategy


@pytest.mark.unit
class TestModelEffectRetryConfigEnumValidation:
    """Test EnumRetryBackoffStrategy enum validation."""

    def test_enum_preserved_not_converted_to_string(self):
        """Test that EnumRetryBackoffStrategy is preserved as enum, not converted to string."""
        config = ModelEffectRetryConfig(
            backoff_strategy=EnumRetryBackoffStrategy.EXPONENTIAL,
        )

        # Should be EnumRetryBackoffStrategy enum, not string
        assert isinstance(config.backoff_strategy, EnumRetryBackoffStrategy)
        assert config.backoff_strategy == EnumRetryBackoffStrategy.EXPONENTIAL
        assert config.backoff_strategy.value == "exponential"

    def test_invalid_enum_string_value_rejected(self):
        """Test that invalid string values for backoff strategy are rejected."""
        # Invalid string should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectRetryConfig(backoff_strategy="invalid_strategy")

        error = exc_info.value
        assert "backoff_strategy" in str(error)

    def test_invalid_enum_numeric_value_rejected(self):
        """Test that numeric values for backoff strategy are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectRetryConfig(backoff_strategy=123)

        error = exc_info.value
        assert "backoff_strategy" in str(error)

    def test_invalid_enum_object_rejected(self):
        """Test that object values for backoff strategy are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectRetryConfig(backoff_strategy={"invalid": "object"})

        error = exc_info.value
        assert "backoff_strategy" in str(error)

    def test_enum_by_valid_string_value_accepted(self):
        """Test that valid enum string values are accepted and converted."""
        # Pydantic should convert valid string to enum
        config = ModelEffectRetryConfig(backoff_strategy="linear")

        assert config.backoff_strategy == EnumRetryBackoffStrategy.LINEAR
        assert isinstance(config.backoff_strategy, EnumRetryBackoffStrategy)

    def test_enum_case_sensitivity(self):
        """Test enum validation case sensitivity."""
        # Lowercase should work (enum values are lowercase)
        config_lower = ModelEffectRetryConfig(backoff_strategy="fibonacci")
        assert config_lower.backoff_strategy == EnumRetryBackoffStrategy.FIBONACCI

        # Uppercase should fail (not a valid enum value)
        with pytest.raises(ValidationError):
            ModelEffectRetryConfig(backoff_strategy="FIBONACCI")

    def test_partial_enum_string_rejected(self):
        """Test that partial enum string values are rejected."""
        with pytest.raises(ValidationError):
            ModelEffectRetryConfig(backoff_strategy="exp")  # partial "exponential"

        with pytest.raises(ValidationError):
            ModelEffectRetryConfig(backoff_strategy="fix")  # partial "fixed"

    def test_all_enum_strategies_by_string(self):
        """Test all enum strategies can be created from string values."""
        strategy_strings = ["fixed", "linear", "exponential", "random", "fibonacci"]

        for strategy_str in strategy_strings:
            config = ModelEffectRetryConfig(backoff_strategy=strategy_str)
            assert config.backoff_strategy.value == strategy_str
            assert isinstance(config.backoff_strategy, EnumRetryBackoffStrategy)

    def test_omit_enum_field_uses_default(self):
        """Test that omitting backoff strategy uses the default."""
        # When field is not provided, default should be used
        config = ModelEffectRetryConfig()

        # Should use default, which is EnumRetryBackoffStrategy.EXPONENTIAL
        assert config.backoff_strategy == EnumRetryBackoffStrategy.EXPONENTIAL

    def test_enum_assignment_validation(self):
        """Test that enum validation works on assignment (validate_assignment=True)."""
        config = ModelEffectRetryConfig()

        # Valid enum assignment
        config.backoff_strategy = EnumRetryBackoffStrategy.FIXED
        assert config.backoff_strategy == EnumRetryBackoffStrategy.FIXED

        # Valid string assignment
        config.backoff_strategy = "linear"
        assert config.backoff_strategy == EnumRetryBackoffStrategy.LINEAR

        # Invalid string assignment should fail
        with pytest.raises(ValidationError):
            config.backoff_strategy = "invalid_strategy"

        # Invalid numeric assignment should fail
        with pytest.raises(ValidationError):
            config.backoff_strategy = 999


@pytest.mark.unit
class TestModelEffectRetryConfigValidation:
    """Test retry configuration validation rules."""

    def test_max_attempts_minimum_value(self):
        """Test max_attempts must be at least 1."""
        config = ModelEffectRetryConfig(max_attempts=1)
        assert config.max_attempts == 1

        with pytest.raises(Exception):
            ModelEffectRetryConfig(max_attempts=0)

        with pytest.raises(Exception):
            ModelEffectRetryConfig(max_attempts=-1)

    def test_base_delay_ms_minimum_value(self):
        """Test base_delay_ms must be at least 1."""
        config = ModelEffectRetryConfig(base_delay_ms=1)
        assert config.base_delay_ms == 1

        with pytest.raises(Exception):
            ModelEffectRetryConfig(base_delay_ms=0)

        with pytest.raises(Exception):
            ModelEffectRetryConfig(base_delay_ms=-1)

    def test_max_delay_ms_minimum_value(self):
        """Test max_delay_ms must be at least 1 and greater than base_delay_ms."""
        # Valid: max > base
        config = ModelEffectRetryConfig(max_delay_ms=2, base_delay_ms=1)
        assert config.max_delay_ms == 2

        with pytest.raises(Exception):
            ModelEffectRetryConfig(max_delay_ms=0)

        with pytest.raises(Exception):
            ModelEffectRetryConfig(max_delay_ms=-1)

    def test_circuit_breaker_threshold_minimum_value(self):
        """Test circuit_breaker_threshold must be at least 1."""
        config = ModelEffectRetryConfig(circuit_breaker_threshold=1)
        assert config.circuit_breaker_threshold == 1

        with pytest.raises(ValidationError):
            ModelEffectRetryConfig(circuit_breaker_threshold=0)

        with pytest.raises(ValidationError):
            ModelEffectRetryConfig(circuit_breaker_threshold=-1)

    def test_circuit_breaker_timeout_s_minimum_value(self):
        """Test circuit_breaker_timeout_s must be at least 1."""
        config = ModelEffectRetryConfig(circuit_breaker_timeout_s=1)
        assert config.circuit_breaker_timeout_s == 1

        with pytest.raises(ValidationError):
            ModelEffectRetryConfig(circuit_breaker_timeout_s=0)

        with pytest.raises(ValidationError):
            ModelEffectRetryConfig(circuit_breaker_timeout_s=-1)


@pytest.mark.unit
class TestModelEffectRetryConfigMaxDelayValidator:
    """Test max_delay_ms validator that enforces it must be greater than base_delay_ms."""

    def test_max_delay_greater_than_base_delay_valid(self):
        """Test max_delay_ms greater than base_delay_ms is valid."""
        config = ModelEffectRetryConfig(base_delay_ms=100, max_delay_ms=5000)
        assert config.base_delay_ms == 100
        assert config.max_delay_ms == 5000

    def test_max_delay_equal_to_base_delay_invalid(self):
        """Test max_delay_ms equal to base_delay_ms raises OnexError."""
        with pytest.raises(OnexError) as exc_info:
            ModelEffectRetryConfig(base_delay_ms=1000, max_delay_ms=1000)

        error = exc_info.value
        assert "max_delay_ms must be greater than base_delay_ms" in str(error)
        assert error.model.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_max_delay_less_than_base_delay_invalid(self):
        """Test max_delay_ms less than base_delay_ms raises OnexError."""
        with pytest.raises(OnexError) as exc_info:
            ModelEffectRetryConfig(base_delay_ms=5000, max_delay_ms=100)

        error = exc_info.value
        assert "max_delay_ms must be greater than base_delay_ms" in str(error)
        assert error.model.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_validator_error_context(self):
        """Test that validator error includes proper context."""
        with pytest.raises(OnexError) as exc_info:
            ModelEffectRetryConfig(base_delay_ms=2000, max_delay_ms=1000)

        error = exc_info.value
        assert error.model.context is not None
        assert "error_type" in error.model.context
        assert "validation_context" in error.model.context

    def test_edge_case_max_delay_one_more_than_base(self):
        """Test max_delay_ms exactly one more than base_delay_ms is valid."""
        config = ModelEffectRetryConfig(base_delay_ms=100, max_delay_ms=101)
        assert config.base_delay_ms == 100
        assert config.max_delay_ms == 101

    def test_edge_case_very_large_delays(self):
        """Test with very large delay values."""
        config = ModelEffectRetryConfig(base_delay_ms=10000, max_delay_ms=100000)
        assert config.base_delay_ms == 10000
        assert config.max_delay_ms == 100000

    def test_validator_triggered_on_construction(self):
        """Test validator is triggered during model construction."""
        # This should work - max > base
        config1 = ModelEffectRetryConfig(base_delay_ms=50, max_delay_ms=500)
        assert config1.max_delay_ms == 500

        # This should fail - max <= base
        with pytest.raises(OnexError):
            ModelEffectRetryConfig(base_delay_ms=500, max_delay_ms=50)


@pytest.mark.unit
class TestModelEffectRetryConfigCircuitBreaker:
    """Test circuit breaker configuration."""

    def test_circuit_breaker_enabled(self):
        """Test circuit breaker enabled configuration."""
        config = ModelEffectRetryConfig(
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout_s=30,
        )

        assert config.circuit_breaker_enabled is True
        assert config.circuit_breaker_threshold == 5
        assert config.circuit_breaker_timeout_s == 30

    def test_circuit_breaker_disabled(self):
        """Test circuit breaker disabled configuration."""
        config = ModelEffectRetryConfig(circuit_breaker_enabled=False)

        assert config.circuit_breaker_enabled is False
        # Other values should still have defaults
        assert config.circuit_breaker_threshold == 3
        assert config.circuit_breaker_timeout_s == 60


@pytest.mark.unit
class TestModelEffectRetryConfigSerialization:
    """Test retry configuration serialization."""

    def test_model_dump(self):
        """Test serialization to dictionary."""
        config = ModelEffectRetryConfig(
            max_attempts=5,
            backoff_strategy=EnumRetryBackoffStrategy.FIBONACCI,
            base_delay_ms=200,
            max_delay_ms=10000,
        )

        data = config.model_dump()

        assert data["max_attempts"] == 5
        assert data["backoff_strategy"] == EnumRetryBackoffStrategy.FIBONACCI
        assert data["base_delay_ms"] == 200
        assert data["max_delay_ms"] == 10000

    def test_model_dump_json(self):
        """Test JSON serialization."""
        config = ModelEffectRetryConfig(
            max_attempts=3,
            backoff_strategy=EnumRetryBackoffStrategy.LINEAR,
        )

        json_str = config.model_dump_json()
        assert isinstance(json_str, str)
        assert "max_attempts" in json_str
        assert "backoff_strategy" in json_str

    def test_round_trip_serialization(self):
        """Test serialization and deserialization."""
        original = ModelEffectRetryConfig(
            max_attempts=7,
            backoff_strategy=EnumRetryBackoffStrategy.RANDOM,
            base_delay_ms=150,
            max_delay_ms=7500,
            jitter_enabled=False,
        )

        # Serialize
        data = original.model_dump()

        # Deserialize
        restored = ModelEffectRetryConfig.model_validate(data)

        assert restored.max_attempts == original.max_attempts
        assert restored.backoff_strategy == original.backoff_strategy
        assert restored.base_delay_ms == original.base_delay_ms
        assert restored.max_delay_ms == original.max_delay_ms
        assert restored.jitter_enabled == original.jitter_enabled


@pytest.mark.unit
class TestModelEffectRetryConfigModelConfig:
    """Test model configuration settings."""

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored."""
        config = ModelEffectRetryConfig(
            max_attempts=3,
            unknown_field="should_be_ignored",
        )

        assert config.max_attempts == 3
        assert not hasattr(config, "unknown_field")

    def test_enum_values_not_converted(self):
        """Test that enum values are preserved."""
        config = ModelEffectRetryConfig(
            backoff_strategy=EnumRetryBackoffStrategy.EXPONENTIAL,
        )

        # Enum should be preserved, not converted to string
        assert isinstance(config.backoff_strategy, EnumRetryBackoffStrategy)
        assert config.backoff_strategy == EnumRetryBackoffStrategy.EXPONENTIAL

    def test_validate_assignment(self):
        """Test that assignment validation is enabled."""
        config = ModelEffectRetryConfig(max_attempts=3)
        assert config.max_attempts == 3

        # Should validate on assignment
        config.max_attempts = 5
        assert config.max_attempts == 5

        # Invalid assignment should fail
        with pytest.raises(ValidationError):
            config.max_attempts = 0


@pytest.mark.unit
class TestModelEffectRetryConfigEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_minimum_valid_configuration(self):
        """Test configuration with minimum valid values."""
        config = ModelEffectRetryConfig(
            max_attempts=1,
            base_delay_ms=1,
            max_delay_ms=2,
            circuit_breaker_threshold=1,
            circuit_breaker_timeout_s=1,
        )

        assert config.max_attempts == 1
        assert config.base_delay_ms == 1
        assert config.max_delay_ms == 2
        assert config.circuit_breaker_threshold == 1
        assert config.circuit_breaker_timeout_s == 1

    def test_high_retry_attempts(self):
        """Test configuration with high retry attempts."""
        config = ModelEffectRetryConfig(max_attempts=100)
        assert config.max_attempts == 100

    def test_all_features_disabled(self):
        """Test configuration with optional features disabled."""
        config = ModelEffectRetryConfig(
            jitter_enabled=False,
            circuit_breaker_enabled=False,
        )

        assert config.jitter_enabled is False
        assert config.circuit_breaker_enabled is False

    def test_all_features_enabled(self):
        """Test configuration with all features enabled."""
        config = ModelEffectRetryConfig(
            jitter_enabled=True,
            circuit_breaker_enabled=True,
        )

        assert config.jitter_enabled is True
        assert config.circuit_breaker_enabled is True
