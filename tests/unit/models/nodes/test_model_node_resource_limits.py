"""
Unit tests for ModelNodeResourceLimits.

Tests all aspects of the node resource limits model including:
- Model instantiation with defaults and custom values
- Resource limit checks
- Resource summary generation
- Constraint evaluation
- Factory methods
- Protocol implementations
- Edge cases and boundary conditions
"""

import pytest

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.model_node_resource_limits import (
    ModelNodeResourceLimits,
)


class TestModelNodeResourceLimits:
    """Test cases for ModelNodeResourceLimits."""

    def test_model_instantiation_default(self):
        """Test that model can be instantiated with defaults."""
        limits = ModelNodeResourceLimits()

        assert limits.max_memory_mb == 1024
        assert limits.max_cpu_percent == 100.0

    def test_model_instantiation_custom(self):
        """Test model instantiation with custom values."""
        limits = ModelNodeResourceLimits(
            max_memory_mb=2048,
            max_cpu_percent=75.0,
        )

        assert limits.max_memory_mb == 2048
        assert limits.max_cpu_percent == 75.0

    def test_has_memory_limit_true(self):
        """Test has_memory_limit returns True when limit is set."""
        limits = ModelNodeResourceLimits(max_memory_mb=512)

        assert limits.has_memory_limit() is True

    def test_has_memory_limit_false(self):
        """Test has_memory_limit returns False when limit is zero."""
        limits = ModelNodeResourceLimits(max_memory_mb=0)

        assert limits.has_memory_limit() is False

    def test_has_cpu_limit_true(self):
        """Test has_cpu_limit returns True when limit is below 100%."""
        limits = ModelNodeResourceLimits(max_cpu_percent=50.0)

        assert limits.has_cpu_limit() is True

    def test_has_cpu_limit_false(self):
        """Test has_cpu_limit returns False when limit is 100%."""
        limits = ModelNodeResourceLimits(max_cpu_percent=100.0)

        assert limits.has_cpu_limit() is False

    def test_has_any_limits_true_memory(self):
        """Test has_any_limits returns True when memory limit exists."""
        limits = ModelNodeResourceLimits(
            max_memory_mb=512,
            max_cpu_percent=100.0,
        )

        assert limits.has_any_limits() is True

    def test_has_any_limits_true_cpu(self):
        """Test has_any_limits returns True when CPU limit exists."""
        limits = ModelNodeResourceLimits(
            max_memory_mb=0,
            max_cpu_percent=75.0,
        )

        assert limits.has_any_limits() is True

    def test_has_any_limits_true_both(self):
        """Test has_any_limits returns True when both limits exist."""
        limits = ModelNodeResourceLimits(
            max_memory_mb=512,
            max_cpu_percent=75.0,
        )

        assert limits.has_any_limits() is True

    def test_has_any_limits_false(self):
        """Test has_any_limits returns False when no limits exist."""
        limits = ModelNodeResourceLimits(
            max_memory_mb=0,
            max_cpu_percent=100.0,
        )

        assert limits.has_any_limits() is False

    def test_get_resource_summary(self):
        """Test get_resource_summary returns correct summary."""
        limits = ModelNodeResourceLimits(
            max_memory_mb=512,
            max_cpu_percent=75.0,
        )

        summary = limits.get_resource_summary()

        assert summary["max_memory_mb"] == 512
        assert summary["max_cpu_percent"] == 75.0
        assert summary["has_memory_limit"] is True
        assert summary["has_cpu_limit"] is True
        assert summary["has_any_limits"] is True

    def test_get_resource_summary_no_limits(self):
        """Test get_resource_summary with no limits."""
        limits = ModelNodeResourceLimits(
            max_memory_mb=0,
            max_cpu_percent=100.0,
        )

        summary = limits.get_resource_summary()

        assert summary["has_memory_limit"] is False
        assert summary["has_cpu_limit"] is False
        assert summary["has_any_limits"] is False

    def test_is_memory_constrained_true(self):
        """Test is_memory_constrained returns True below threshold."""
        limits = ModelNodeResourceLimits(max_memory_mb=512)

        assert limits.is_memory_constrained(threshold_mb=1024) is True

    def test_is_memory_constrained_false(self):
        """Test is_memory_constrained returns False above threshold."""
        limits = ModelNodeResourceLimits(max_memory_mb=2048)

        assert limits.is_memory_constrained(threshold_mb=1024) is False

    def test_is_memory_constrained_exact_threshold(self):
        """Test is_memory_constrained at exact threshold."""
        limits = ModelNodeResourceLimits(max_memory_mb=1024)

        assert limits.is_memory_constrained(threshold_mb=1024) is False

    def test_is_memory_constrained_custom_threshold(self):
        """Test is_memory_constrained with custom threshold."""
        limits = ModelNodeResourceLimits(max_memory_mb=512)

        assert limits.is_memory_constrained(threshold_mb=2048) is True
        assert limits.is_memory_constrained(threshold_mb=256) is False

    def test_is_cpu_constrained_true(self):
        """Test is_cpu_constrained returns True below threshold."""
        limits = ModelNodeResourceLimits(max_cpu_percent=25.0)

        assert limits.is_cpu_constrained(threshold_percent=50.0) is True

    def test_is_cpu_constrained_false(self):
        """Test is_cpu_constrained returns False above threshold."""
        limits = ModelNodeResourceLimits(max_cpu_percent=75.0)

        assert limits.is_cpu_constrained(threshold_percent=50.0) is False

    def test_is_cpu_constrained_exact_threshold(self):
        """Test is_cpu_constrained at exact threshold."""
        limits = ModelNodeResourceLimits(max_cpu_percent=50.0)

        assert limits.is_cpu_constrained(threshold_percent=50.0) is False

    def test_is_cpu_constrained_custom_threshold(self):
        """Test is_cpu_constrained with custom threshold."""
        limits = ModelNodeResourceLimits(max_cpu_percent=30.0)

        assert limits.is_cpu_constrained(threshold_percent=75.0) is True
        assert limits.is_cpu_constrained(threshold_percent=20.0) is False


class TestModelNodeResourceLimitsFactoryMethods:
    """Test factory methods."""

    def test_create_unlimited_factory(self):
        """Test create_unlimited factory method."""
        limits = ModelNodeResourceLimits.create_unlimited()

        assert limits.max_memory_mb == 1024
        assert limits.max_cpu_percent == 100.0

    def test_create_constrained_memory_only(self):
        """Test create_constrained with memory limit only."""
        limits = ModelNodeResourceLimits.create_constrained(memory_mb=512)

        assert limits.max_memory_mb == 512
        assert limits.max_cpu_percent == 100.0

    def test_create_constrained_cpu_only(self):
        """Test create_constrained with CPU limit only."""
        limits = ModelNodeResourceLimits.create_constrained(cpu_percent=75.0)

        assert limits.max_memory_mb == 1024
        assert limits.max_cpu_percent == 75.0

    def test_create_constrained_both(self):
        """Test create_constrained with both limits."""
        limits = ModelNodeResourceLimits.create_constrained(
            memory_mb=512,
            cpu_percent=75.0,
        )

        assert limits.max_memory_mb == 512
        assert limits.max_cpu_percent == 75.0

    def test_create_constrained_none_values(self):
        """Test create_constrained with None values uses defaults."""
        limits = ModelNodeResourceLimits.create_constrained(
            memory_mb=None,
            cpu_percent=None,
        )

        assert limits.max_memory_mb == 1024
        assert limits.max_cpu_percent == 100.0


class TestModelNodeResourceLimitsProtocols:
    """Test protocol implementations."""

    def test_get_id_protocol_raises_error(self):
        """Test get_id protocol method raises error (no ID field)."""
        limits = ModelNodeResourceLimits()

        with pytest.raises(ModelOnexError) as exc_info:
            limits.get_id()

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "must have a valid ID field" in str(exc_info.value)

    def test_get_metadata_protocol(self):
        """Test get_metadata protocol method."""
        limits = ModelNodeResourceLimits()

        metadata = limits.get_metadata()
        assert isinstance(metadata, dict)

    def test_set_metadata_protocol(self):
        """Test set_metadata protocol method."""
        limits = ModelNodeResourceLimits()

        result = limits.set_metadata({"max_memory_mb": 2048})
        assert result is True
        assert limits.max_memory_mb == 2048

    def test_set_metadata_protocol_unknown_field(self):
        """Test set_metadata with unknown field."""
        limits = ModelNodeResourceLimits()

        result = limits.set_metadata({"unknown_field": "value"})
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        limits = ModelNodeResourceLimits()

        serialized = limits.serialize()
        assert isinstance(serialized, dict)
        assert "max_memory_mb" in serialized
        assert "max_cpu_percent" in serialized

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol method."""
        limits = ModelNodeResourceLimits()

        assert limits.validate_instance() is True


class TestModelNodeResourceLimitsEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_model_config_extra_ignore(self):
        """Test that model ignores extra fields."""
        limits = ModelNodeResourceLimits(extra_field="ignored")

        assert limits.max_memory_mb == 1024

    def test_model_config_validate_assignment(self):
        """Test that model validates on assignment."""
        limits = ModelNodeResourceLimits()

        limits.max_memory_mb = 2048
        assert limits.max_memory_mb == 2048

    def test_memory_limit_zero(self):
        """Test memory limit can be zero."""
        limits = ModelNodeResourceLimits(max_memory_mb=0)

        assert limits.max_memory_mb == 0
        assert limits.has_memory_limit() is False

    def test_memory_limit_large_value(self):
        """Test memory limit with very large value."""
        limits = ModelNodeResourceLimits(max_memory_mb=100000)

        assert limits.max_memory_mb == 100000
        assert limits.has_memory_limit() is True

    def test_cpu_limit_minimum(self):
        """Test CPU limit at minimum (0.0)."""
        limits = ModelNodeResourceLimits(max_cpu_percent=0.0)

        assert limits.max_cpu_percent == 0.0
        assert limits.has_cpu_limit() is True

    def test_cpu_limit_maximum(self):
        """Test CPU limit at maximum (100.0)."""
        limits = ModelNodeResourceLimits(max_cpu_percent=100.0)

        assert limits.max_cpu_percent == 100.0
        assert limits.has_cpu_limit() is False

    def test_cpu_limit_fractional(self):
        """Test CPU limit with fractional percentage."""
        limits = ModelNodeResourceLimits(max_cpu_percent=33.33)

        assert limits.max_cpu_percent == 33.33
        assert limits.has_cpu_limit() is True

    def test_serialize_includes_all_fields(self):
        """Test serialize includes all fields."""
        limits = ModelNodeResourceLimits()

        serialized = limits.serialize()

        expected_fields = ["max_memory_mb", "max_cpu_percent"]

        for field in expected_fields:
            assert field in serialized

    def test_memory_validation_boundary(self):
        """Test memory validation enforces >= 0."""
        # Should work at boundary
        limits = ModelNodeResourceLimits(max_memory_mb=0)
        assert limits.max_memory_mb == 0

        # Negative should fail validation
        with pytest.raises(Exception):
            ModelNodeResourceLimits(max_memory_mb=-1)

    def test_cpu_validation_boundaries(self):
        """Test CPU validation enforces 0.0 <= value <= 100.0."""
        # Lower boundary
        limits_min = ModelNodeResourceLimits(max_cpu_percent=0.0)
        assert limits_min.max_cpu_percent == 0.0

        # Upper boundary
        limits_max = ModelNodeResourceLimits(max_cpu_percent=100.0)
        assert limits_max.max_cpu_percent == 100.0

        # Below lower boundary should fail
        with pytest.raises(Exception):
            ModelNodeResourceLimits(max_cpu_percent=-0.1)

        # Above upper boundary should fail
        with pytest.raises(Exception):
            ModelNodeResourceLimits(max_cpu_percent=100.1)

    def test_resource_summary_updates_with_changes(self):
        """Test resource summary reflects dynamic changes."""
        # Start with no limits (memory=0, cpu=100)
        limits = ModelNodeResourceLimits(max_memory_mb=0, max_cpu_percent=100.0)

        summary1 = limits.get_resource_summary()
        assert summary1["has_any_limits"] is False

        limits.max_cpu_percent = 50.0
        summary2 = limits.get_resource_summary()
        assert summary2["has_cpu_limit"] is True
        assert summary2["has_any_limits"] is True

    def test_constraint_checks_with_default_thresholds(self):
        """Test constraint checks use correct default thresholds."""
        limits = ModelNodeResourceLimits(
            max_memory_mb=512,
            max_cpu_percent=25.0,
        )

        # Default memory threshold is 1024
        assert limits.is_memory_constrained() is True

        # Default CPU threshold is 50.0
        assert limits.is_cpu_constrained() is True
