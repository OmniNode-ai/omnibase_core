"""
Tests for ModelResourceUsageMetric.

Validates resource usage metric configuration including
percentage range validation.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_resource_unit import EnumResourceUnit
from omnibase_core.models.contracts.subcontracts.model_resource_usage_metric import (
    ModelResourceUsageMetric,
)


class TestModelResourceUsageMetricValidation:
    """Test validation rules for resource usage metrics."""

    def test_valid_percentage_within_range(self) -> None:
        """Test that percentage values <= 150 are valid."""
        # Test at boundary
        metric = ModelResourceUsageMetric(
            resource_name="cpu",
            usage_value=150.0,
            is_percentage=True,
        )
        assert metric.usage_value == 150.0
        assert metric.is_percentage is True

        # Test well within range
        metric = ModelResourceUsageMetric(
            resource_name="memory",
            usage_value=85.5,
            is_percentage=True,
        )
        assert metric.usage_value == 85.5

        # Test at zero
        metric = ModelResourceUsageMetric(
            resource_name="disk",
            usage_value=0.0,
            is_percentage=True,
        )
        assert metric.usage_value == 0.0

    def test_invalid_percentage_exceeds_maximum(self) -> None:
        """Test that percentage values > 150 raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelResourceUsageMetric(
                resource_name="cpu",
                usage_value=151.0,
                is_percentage=True,
            )

        error_msg = str(exc_info.value)
        assert "151.0" in error_msg
        assert "150%" in error_msg
        assert "is_percentage=False" in error_msg

    def test_invalid_percentage_far_exceeds_maximum(self) -> None:
        """Test that percentage values far above 150 raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelResourceUsageMetric(
                resource_name="memory",
                usage_value=999.9,
                is_percentage=True,
            )

        error_msg = str(exc_info.value)
        assert "999.9" in error_msg
        assert "exceeds maximum" in error_msg

    def test_valid_non_percentage_high_values(self) -> None:
        """Test that non-percentage metrics can have values > 150."""
        # High byte count
        metric = ModelResourceUsageMetric(
            resource_name="memory",
            usage_value=8589934592.0,  # 8GB in bytes
            usage_unit=EnumResourceUnit.BYTES,
            is_percentage=False,
        )
        assert metric.usage_value == 8589934592.0
        assert metric.is_percentage is False

        # High IOPS count
        metric = ModelResourceUsageMetric(
            resource_name="disk",
            usage_value=10000.0,
            usage_unit=EnumResourceUnit.IOPS,
            is_percentage=False,
        )
        assert metric.usage_value == 10000.0

    def test_non_percentage_with_high_value_and_percentage_flag_false(self) -> None:
        """Test that is_percentage=False allows any high value."""
        metric = ModelResourceUsageMetric(
            resource_name="network",
            usage_value=1000000.0,
            usage_unit=EnumResourceUnit.MBPS,
            is_percentage=False,
        )
        assert metric.usage_value == 1000000.0
        assert metric.is_percentage is False


class TestModelResourceUsageMetricCreation:
    """Test creation and field constraints."""

    def test_required_fields(self) -> None:
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            ModelResourceUsageMetric()  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            ModelResourceUsageMetric(resource_name="cpu")  # Missing usage_value

        with pytest.raises(ValidationError):
            ModelResourceUsageMetric(usage_value=50.0)  # Missing resource_name

    def test_default_values(self) -> None:
        """Test default field values."""
        metric = ModelResourceUsageMetric(
            resource_name="cpu",
            usage_value=75.0,
        )
        assert metric.usage_unit == EnumResourceUnit.PERCENTAGE
        assert metric.is_percentage is True
        assert metric.max_value is None
        assert metric.threshold_warning is None
        assert metric.threshold_critical is None

    def test_optional_fields(self) -> None:
        """Test optional field assignment."""
        metric = ModelResourceUsageMetric(
            resource_name="memory",
            usage_value=8192.0,
            usage_unit=EnumResourceUnit.BYTES,
            max_value=16384.0,
            threshold_warning=12288.0,
            threshold_critical=14336.0,
            is_percentage=False,
        )
        assert metric.usage_unit == EnumResourceUnit.BYTES
        assert metric.max_value == 16384.0
        assert metric.threshold_warning == 12288.0
        assert metric.threshold_critical == 14336.0
        assert metric.is_percentage is False

    def test_string_field_constraints(self) -> None:
        """Test string field minimum length constraints."""
        with pytest.raises(ValidationError):
            ModelResourceUsageMetric(
                resource_name="",  # Empty string not allowed
                usage_value=50.0,
            )

    def test_numeric_field_constraints(self) -> None:
        """Test numeric field constraints (non-negative values)."""
        with pytest.raises(ValidationError):
            ModelResourceUsageMetric(
                resource_name="cpu",
                usage_value=-10.0,  # Must be >= 0
            )

        with pytest.raises(ValidationError):
            ModelResourceUsageMetric(
                resource_name="cpu",
                usage_value=50.0,
                max_value=-100.0,  # Must be >= 0
            )

        with pytest.raises(ValidationError):
            ModelResourceUsageMetric(
                resource_name="cpu",
                usage_value=50.0,
                threshold_warning=-50.0,  # Must be >= 0
            )

    def test_enum_values_for_usage_unit(self) -> None:
        """Test that usage_unit accepts all valid enum values."""
        for unit in EnumResourceUnit:
            metric = ModelResourceUsageMetric(
                resource_name="test_resource",
                usage_value=100.0,
                usage_unit=unit,
                is_percentage=False,  # Use False to allow high values
            )
            assert metric.usage_unit == unit


class TestModelResourceUsageMetricEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_percentage_at_exactly_150(self) -> None:
        """Test that exactly 150.0 is allowed for percentages."""
        metric = ModelResourceUsageMetric(
            resource_name="cpu",
            usage_value=150.0,
            is_percentage=True,
        )
        assert metric.usage_value == 150.0

    def test_percentage_just_above_150(self) -> None:
        """Test that 150.01 is rejected for percentages."""
        with pytest.raises(ValidationError):
            ModelResourceUsageMetric(
                resource_name="cpu",
                usage_value=150.01,
                is_percentage=True,
            )

    def test_high_value_with_percentage_unit_but_flag_false(self) -> None:
        """Test that high values are allowed when is_percentage=False."""
        # Even with PERCENTAGE unit, if is_percentage=False, allow high values
        metric = ModelResourceUsageMetric(
            resource_name="custom_metric",
            usage_value=500.0,
            usage_unit=EnumResourceUnit.PERCENTAGE,
            is_percentage=False,
        )
        assert metric.usage_value == 500.0
        assert metric.is_percentage is False

    def test_zero_usage_value(self) -> None:
        """Test that zero usage values are valid."""
        metric = ModelResourceUsageMetric(
            resource_name="idle_cpu",
            usage_value=0.0,
            is_percentage=True,
        )
        assert metric.usage_value == 0.0

    def test_fractional_percentage_values(self) -> None:
        """Test that fractional percentage values are valid."""
        metric = ModelResourceUsageMetric(
            resource_name="cpu",
            usage_value=99.999,
            is_percentage=True,
        )
        assert metric.usage_value == 99.999
