"""
Unit tests for ModelRetrySubcontract.

Comprehensive test coverage for retry subcontract model including:
- Field validation and constraints
- Business rule validation
- INTERFACE_VERSION accessibility
- ConfigDict behavior
- Edge cases and error scenarios
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)

from omnibase_core.models.contracts.subcontracts.model_retry_subcontract import (
    ModelRetrySubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.mark.unit
class TestModelRetrySubcontractBasics:
    """Test basic model instantiation and defaults."""

    def test_default_instantiation(self):
        """Test model can be instantiated with defaults."""
        retry = ModelRetrySubcontract(version=DEFAULT_VERSION)

        assert retry.max_retries == 3
        assert retry.base_delay_seconds == 1.0
        assert retry.backoff_strategy == "exponential"
        assert retry.backoff_multiplier == 2.0
        assert retry.max_delay_seconds == 60.0
        assert retry.jitter_enabled is True
        assert retry.jitter_factor == 0.1
        assert retry.circuit_breaker_enabled is False
        assert retry.retry_on_timeout is True
        assert retry.exponential_cap_enabled is True

    def test_custom_values(self):
        """Test model accepts custom values."""
        retry = ModelRetrySubcontract(
            version=DEFAULT_VERSION,
            max_retries=5,
            base_delay_seconds=2.0,
            backoff_strategy="linear",
            backoff_multiplier=3.0,
            max_delay_seconds=120.0,
            jitter_enabled=False,
        )

        assert retry.max_retries == 5
        assert retry.base_delay_seconds == 2.0
        assert retry.backoff_strategy == "linear"
        assert retry.backoff_multiplier == 3.0
        assert retry.max_delay_seconds == 120.0
        assert retry.jitter_enabled is False

    def test_interface_version_accessible(self):
        """Test INTERFACE_VERSION is accessible as ClassVar."""
        assert hasattr(ModelRetrySubcontract, "INTERFACE_VERSION")
        assert isinstance(ModelRetrySubcontract.INTERFACE_VERSION, ModelSemVer)
        assert ModelRetrySubcontract.INTERFACE_VERSION.major == 1
        assert ModelRetrySubcontract.INTERFACE_VERSION.minor == 0
        assert ModelRetrySubcontract.INTERFACE_VERSION.patch == 0

    def test_retryable_error_codes_default(self):
        """Test retryable error codes have sensible defaults."""
        retry = ModelRetrySubcontract(version=DEFAULT_VERSION)

        assert "timeout" in retry.retryable_error_codes
        assert "network_error" in retry.retryable_error_codes
        assert "service_unavailable" in retry.retryable_error_codes
        assert "rate_limit" in retry.retryable_error_codes

    def test_non_retryable_error_codes_default(self):
        """Test non-retryable error codes have sensible defaults."""
        retry = ModelRetrySubcontract(version=DEFAULT_VERSION)

        assert "authentication_error" in retry.non_retryable_error_codes
        assert "authorization_error" in retry.non_retryable_error_codes
        assert "not_found" in retry.non_retryable_error_codes
        assert "validation_error" in retry.non_retryable_error_codes


@pytest.mark.unit
class TestModelRetrySubcontractValidation:
    """Test field validation and constraints."""

    def test_max_retries_bounds(self):
        """Test max_retries validates bounds."""
        # Valid values
        ModelRetrySubcontract(version=DEFAULT_VERSION, max_retries=0)  # No retries
        ModelRetrySubcontract(version=DEFAULT_VERSION, max_retries=50)
        ModelRetrySubcontract(version=DEFAULT_VERSION, max_retries=100)  # Max

        # Invalid values
        with pytest.raises(ValidationError):
            ModelRetrySubcontract(version=DEFAULT_VERSION, max_retries=-1)

        with pytest.raises(ValidationError):
            ModelRetrySubcontract(version=DEFAULT_VERSION, max_retries=101)

    def test_base_delay_seconds_bounds(self):
        """Test base_delay_seconds validates bounds."""
        # Valid values
        ModelRetrySubcontract(
            version=DEFAULT_VERSION, base_delay_seconds=0.1
        )  # Min (default max_delay_seconds=60.0 is fine)
        ModelRetrySubcontract(
            version=DEFAULT_VERSION, base_delay_seconds=10.0
        )  # (default max_delay_seconds=60.0 is fine)
        ModelRetrySubcontract(
            version=DEFAULT_VERSION,
            base_delay_seconds=3600.0,  # Max
            max_delay_seconds=3600.0,  # Must be >= base_delay_seconds
        )

        # Invalid values
        with pytest.raises(ValidationError):
            ModelRetrySubcontract(
                version=DEFAULT_VERSION,
                base_delay_seconds=0.05,  # Below minimum (0.1)
                max_delay_seconds=1.0,  # Valid max to isolate base_delay validation
            )

        with pytest.raises(ValidationError):
            ModelRetrySubcontract(
                version=DEFAULT_VERSION,
                base_delay_seconds=3601.0,  # Above maximum (3600.0)
                max_delay_seconds=3601.0,  # Valid max to isolate base_delay validation
            )

    def test_backoff_strategy_validation(self):
        """Test backoff_strategy validates allowed values."""
        # Valid strategies
        ModelRetrySubcontract(version=DEFAULT_VERSION, backoff_strategy="exponential")
        ModelRetrySubcontract(version=DEFAULT_VERSION, backoff_strategy="linear")
        ModelRetrySubcontract(version=DEFAULT_VERSION, backoff_strategy="constant")

        # Invalid strategy
        with pytest.raises(ModelOnexError) as exc_info:
            ModelRetrySubcontract(version=DEFAULT_VERSION, backoff_strategy="invalid")

        assert "must be one of" in str(exc_info.value)

    def test_backoff_multiplier_bounds(self):
        """Test backoff_multiplier validates bounds."""
        # Valid values
        ModelRetrySubcontract(version=DEFAULT_VERSION, backoff_multiplier=1.0)  # Min
        ModelRetrySubcontract(version=DEFAULT_VERSION, backoff_multiplier=5.0)
        ModelRetrySubcontract(version=DEFAULT_VERSION, backoff_multiplier=10.0)  # Max

        # Invalid values
        with pytest.raises(ValidationError):
            ModelRetrySubcontract(version=DEFAULT_VERSION, backoff_multiplier=0.5)

        with pytest.raises(ValidationError):
            ModelRetrySubcontract(version=DEFAULT_VERSION, backoff_multiplier=11.0)

    def test_max_delay_seconds_bounds(self):
        """Test max_delay_seconds validates bounds."""
        # Valid values
        ModelRetrySubcontract(version=DEFAULT_VERSION, max_delay_seconds=1.0)  # Min
        ModelRetrySubcontract(version=DEFAULT_VERSION, max_delay_seconds=60.0)
        ModelRetrySubcontract(version=DEFAULT_VERSION, max_delay_seconds=3600.0)  # Max

        # Invalid values
        with pytest.raises(ValidationError):
            ModelRetrySubcontract(version=DEFAULT_VERSION, max_delay_seconds=0.5)

        with pytest.raises(ValidationError):
            ModelRetrySubcontract(version=DEFAULT_VERSION, max_delay_seconds=3601.0)

    def test_max_delay_greater_than_base_delay(self):
        """Test max_delay_seconds must be >= base_delay_seconds."""
        # Valid: max_delay >= base_delay
        ModelRetrySubcontract(
            version=DEFAULT_VERSION, base_delay_seconds=2.0, max_delay_seconds=2.0
        )
        ModelRetrySubcontract(
            version=DEFAULT_VERSION, base_delay_seconds=2.0, max_delay_seconds=10.0
        )

        # Invalid: max_delay < base_delay
        with pytest.raises(ModelOnexError) as exc_info:
            ModelRetrySubcontract(
                version=DEFAULT_VERSION, base_delay_seconds=10.0, max_delay_seconds=5.0
            )

        assert "must be >=" in str(exc_info.value)

    def test_jitter_factor_bounds(self):
        """Test jitter_factor validates bounds."""
        # Valid values
        ModelRetrySubcontract(version=DEFAULT_VERSION, jitter_factor=0.0)  # Min
        ModelRetrySubcontract(version=DEFAULT_VERSION, jitter_factor=0.25)
        ModelRetrySubcontract(version=DEFAULT_VERSION, jitter_factor=0.5)  # Max

        # Invalid values
        with pytest.raises(ValidationError):
            ModelRetrySubcontract(version=DEFAULT_VERSION, jitter_factor=-0.1)

        # Pydantic constraint validation catches values > 0.5
        with pytest.raises(ValidationError):
            ModelRetrySubcontract(version=DEFAULT_VERSION, jitter_factor=0.6)

    def test_timeout_per_attempt_bounds(self):
        """Test timeout_per_attempt_seconds validates bounds."""
        # Valid values (need to set max_delay_seconds to avoid cross-field validation)
        ModelRetrySubcontract(
            version=DEFAULT_VERSION,
            timeout_per_attempt_seconds=0.1,
            max_delay_seconds=1.0,
        )  # Min
        ModelRetrySubcontract(
            version=DEFAULT_VERSION,
            timeout_per_attempt_seconds=60.0,
            max_delay_seconds=60.0,
        )
        ModelRetrySubcontract(
            version=DEFAULT_VERSION,
            timeout_per_attempt_seconds=3600.0,
            max_delay_seconds=3600.0,
        )  # Max
        ModelRetrySubcontract(
            version=DEFAULT_VERSION, timeout_per_attempt_seconds=None
        )  # Disabled

        # Invalid values
        with pytest.raises(ValidationError):
            ModelRetrySubcontract(
                version=DEFAULT_VERSION,
                timeout_per_attempt_seconds=0.05,
                max_delay_seconds=1.0,
            )

        with pytest.raises(ValidationError):
            ModelRetrySubcontract(
                version=DEFAULT_VERSION,
                timeout_per_attempt_seconds=3601.0,
                max_delay_seconds=3601.0,
            )

    def test_timeout_per_attempt_reasonable_vs_max_delay(self):
        """Test timeout_per_attempt should not exceed 2x max_delay."""
        # Valid: timeout <= 2x max_delay
        ModelRetrySubcontract(
            version=DEFAULT_VERSION,
            max_delay_seconds=60.0,
            timeout_per_attempt_seconds=120.0,  # Exactly 2x
        )

        # Invalid: timeout > 2x max_delay
        with pytest.raises(ModelOnexError) as exc_info:
            ModelRetrySubcontract(
                version=DEFAULT_VERSION,
                max_delay_seconds=10.0,
                timeout_per_attempt_seconds=25.0,  # More than 2x
            )

        assert "should not exceed 2x" in str(exc_info.value)


@pytest.mark.unit
class TestModelRetrySubcontractEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_retries_configuration(self):
        """Test configuration with zero retries (fail-fast mode)."""
        retry = ModelRetrySubcontract(version=DEFAULT_VERSION, max_retries=0)

        assert retry.max_retries == 0
        # Other fields should still have valid defaults

    def test_no_jitter_configuration(self):
        """Test configuration with jitter disabled."""
        retry = ModelRetrySubcontract(
            version=DEFAULT_VERSION, jitter_enabled=False, jitter_factor=0.0
        )

        assert retry.jitter_enabled is False
        assert retry.jitter_factor == 0.0

    def test_constant_backoff_configuration(self):
        """Test constant backoff strategy configuration."""
        retry = ModelRetrySubcontract(
            version=DEFAULT_VERSION,
            backoff_strategy="constant",
            base_delay_seconds=5.0,
            backoff_multiplier=1.0,  # Ignored for constant
        )

        assert retry.backoff_strategy == "constant"
        assert retry.backoff_multiplier == 1.0

    def test_linear_backoff_configuration(self):
        """Test linear backoff strategy configuration."""
        retry = ModelRetrySubcontract(
            version=DEFAULT_VERSION,
            backoff_strategy="linear",
            base_delay_seconds=2.0,
            max_delay_seconds=20.0,
        )

        assert retry.backoff_strategy == "linear"

    def test_aggressive_retry_configuration(self):
        """Test aggressive retry configuration with many attempts."""
        retry = ModelRetrySubcontract(
            version=DEFAULT_VERSION,
            max_retries=100,
            base_delay_seconds=0.1,
            max_delay_seconds=10.0,
        )

        assert retry.max_retries == 100
        assert retry.base_delay_seconds == 0.1

    def test_conservative_retry_configuration(self):
        """Test conservative retry configuration with few attempts."""
        retry = ModelRetrySubcontract(
            version=DEFAULT_VERSION,
            max_retries=1,
            base_delay_seconds=5.0,
            max_delay_seconds=5.0,  # No exponential growth
        )

        assert retry.max_retries == 1
        assert retry.base_delay_seconds == 5.0
        assert retry.max_delay_seconds == 5.0

    def test_circuit_breaker_integration(self):
        """Test circuit breaker integration flag."""
        retry = ModelRetrySubcontract(
            version=DEFAULT_VERSION, circuit_breaker_enabled=True
        )

        assert retry.circuit_breaker_enabled is True

    def test_custom_error_codes(self):
        """Test custom error code lists."""
        retry = ModelRetrySubcontract(
            version=DEFAULT_VERSION,
            retryable_error_codes=["custom_error_1", "custom_error_2"],
            non_retryable_error_codes=["permanent_error"],
        )

        assert "custom_error_1" in retry.retryable_error_codes
        assert "custom_error_2" in retry.retryable_error_codes
        assert "permanent_error" in retry.non_retryable_error_codes


@pytest.mark.unit
class TestModelRetrySubcontractConfigDict:
    """Test ConfigDict behavior."""

    def test_extra_fields_ignored(self):
        """Test extra fields are ignored per ConfigDict."""
        retry = ModelRetrySubcontract(
            version=DEFAULT_VERSION,
            max_retries=3,
            unknown_field="should_be_ignored",
        )

        assert retry.max_retries == 3
        assert not hasattr(retry, "unknown_field")

    def test_validate_assignment(self):
        """Test assignment validation is enabled."""
        retry = ModelRetrySubcontract(version=DEFAULT_VERSION)

        # Valid assignment
        retry.max_retries = 5
        assert retry.max_retries == 5

        # Invalid assignment should raise
        with pytest.raises(ValidationError):
            retry.max_retries = -1

    def test_model_serialization(self):
        """Test model can be serialized and deserialized."""
        original = ModelRetrySubcontract(
            version=DEFAULT_VERSION,
            max_retries=5,
            base_delay_seconds=2.0,
            backoff_strategy="linear",
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize
        restored = ModelRetrySubcontract(**data)

        assert restored.max_retries == original.max_retries
        assert restored.base_delay_seconds == original.base_delay_seconds
        assert restored.backoff_strategy == original.backoff_strategy


@pytest.mark.unit
class TestModelRetrySubcontractDocumentation:
    """Test documentation and interface guarantees."""

    def test_docstring_present(self):
        """Test model has comprehensive docstring."""
        assert ModelRetrySubcontract.__doc__ is not None
        assert len(ModelRetrySubcontract.__doc__) > 100

    def test_field_descriptions(self):
        """Test all fields have descriptions."""
        schema = ModelRetrySubcontract.model_json_schema()

        for field_name, field_info in schema.get("properties", {}).items():
            assert "description" in field_info, (
                f"Field {field_name} missing description"
            )

    def test_interface_stability(self):
        """Test interface version guarantees stability."""
        version = ModelRetrySubcontract.INTERFACE_VERSION

        # Interface version should be 1.0.0 for initial release
        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0

        # Version should be immutable
        assert ModelRetrySubcontract.INTERFACE_VERSION.model_config["frozen"] is True
