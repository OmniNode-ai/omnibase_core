"""
Comprehensive tests for ModelOrchestratorMetrics.

Tests cover:
- Basic instantiation with default values
- Field validation and type safety
- Method functionality (get_total_workflows, get_success_rate)
- Numeric field handling (integers and floats)
- Edge cases for calculations
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.results.model_orchestrator_metrics import (
    ModelOrchestratorMetrics,
)


class TestModelOrchestratorMetricsBasicInstantiation:
    """Test basic instantiation."""

    def test_empty_instantiation_with_defaults(self):
        """Test creating metrics with default values."""
        metrics = ModelOrchestratorMetrics()

        assert metrics.active_workflows == 0
        assert metrics.completed_workflows == 0
        assert metrics.failed_workflows == 0
        assert metrics.avg_execution_time_seconds is None
        assert metrics.resource_utilization_percent is None

    def test_instantiation_with_workflow_counts(self):
        """Test creating metrics with workflow counts."""
        metrics = ModelOrchestratorMetrics(
            active_workflows=5,
            completed_workflows=100,
            failed_workflows=3,
        )

        assert metrics.active_workflows == 5
        assert metrics.completed_workflows == 100
        assert metrics.failed_workflows == 3

    def test_instantiation_with_all_fields(self):
        """Test creating metrics with all fields populated."""
        metrics = ModelOrchestratorMetrics(
            active_workflows=10,
            completed_workflows=200,
            failed_workflows=5,
            avg_execution_time_seconds=45.5,
            resource_utilization_percent=75.0,
        )

        assert metrics.active_workflows == 10
        assert metrics.completed_workflows == 200
        assert metrics.failed_workflows == 5
        assert metrics.avg_execution_time_seconds == 45.5
        assert metrics.resource_utilization_percent == 75.0


class TestModelOrchestratorMetricsFieldValidation:
    """Test field validation and type safety."""

    def test_workflow_counts_must_be_integers(self):
        """Test that workflow count fields must be integers."""
        metrics = ModelOrchestratorMetrics(
            active_workflows=5,
            completed_workflows=10,
            failed_workflows=2,
        )

        assert isinstance(metrics.active_workflows, int)
        assert isinstance(metrics.completed_workflows, int)
        assert isinstance(metrics.failed_workflows, int)

    def test_workflow_counts_default_to_zero(self):
        """Test that workflow count fields default to 0."""
        metrics = ModelOrchestratorMetrics()

        assert metrics.active_workflows == 0
        assert metrics.completed_workflows == 0
        assert metrics.failed_workflows == 0

    def test_negative_workflow_counts_rejected(self):
        """Test that negative workflow counts are rejected."""
        with pytest.raises(ValidationError):
            ModelOrchestratorMetrics(active_workflows=-1)

        with pytest.raises(ValidationError):
            ModelOrchestratorMetrics(completed_workflows=-1)

        with pytest.raises(ValidationError):
            ModelOrchestratorMetrics(failed_workflows=-1)


class TestModelOrchestratorMetricsExecutionTimeField:
    """Test average execution time field."""

    def test_avg_execution_time_as_float(self):
        """Test avg_execution_time_seconds as float."""
        metrics = ModelOrchestratorMetrics(avg_execution_time_seconds=45.5)

        assert metrics.avg_execution_time_seconds == 45.5
        assert isinstance(metrics.avg_execution_time_seconds, float)

    def test_avg_execution_time_as_integer(self):
        """Test avg_execution_time_seconds as integer (coerced to float)."""
        metrics = ModelOrchestratorMetrics(avg_execution_time_seconds=30)

        assert metrics.avg_execution_time_seconds == 30
        # Pydantic may keep it as int, both are acceptable

    def test_avg_execution_time_optional(self):
        """Test that avg_execution_time_seconds is optional."""
        metrics = ModelOrchestratorMetrics()
        assert metrics.avg_execution_time_seconds is None

    def test_avg_execution_time_zero(self):
        """Test avg_execution_time_seconds with zero value."""
        metrics = ModelOrchestratorMetrics(avg_execution_time_seconds=0.0)
        assert metrics.avg_execution_time_seconds == 0.0


class TestModelOrchestratorMetricsResourceUtilizationField:
    """Test resource utilization percentage field."""

    def test_resource_utilization_as_percentage(self):
        """Test resource_utilization_percent as percentage value."""
        metrics = ModelOrchestratorMetrics(resource_utilization_percent=75.5)

        assert metrics.resource_utilization_percent == 75.5
        assert isinstance(metrics.resource_utilization_percent, float)

    def test_resource_utilization_boundary_values(self):
        """Test resource_utilization_percent with boundary values."""
        # 0%
        metrics = ModelOrchestratorMetrics(resource_utilization_percent=0.0)
        assert metrics.resource_utilization_percent == 0.0

        # 100%
        metrics = ModelOrchestratorMetrics(resource_utilization_percent=100.0)
        assert metrics.resource_utilization_percent == 100.0

    def test_resource_utilization_optional(self):
        """Test that resource_utilization_percent is optional."""
        metrics = ModelOrchestratorMetrics()
        assert metrics.resource_utilization_percent is None


class TestModelOrchestratorMetricsGetTotalWorkflows:
    """Test get_total_workflows() method."""

    def test_get_total_workflows_with_values(self):
        """Test get_total_workflows() calculation."""
        metrics = ModelOrchestratorMetrics(
            active_workflows=5,
            completed_workflows=100,
            failed_workflows=3,
        )

        total = metrics.get_total_workflows()

        assert total == 108  # 5 + 100 + 3

    def test_get_total_workflows_with_zeros(self):
        """Test get_total_workflows() when all counts are zero."""
        metrics = ModelOrchestratorMetrics()

        total = metrics.get_total_workflows()

        assert total == 0

    def test_get_total_workflows_with_only_active(self):
        """Test get_total_workflows() with only active workflows."""
        metrics = ModelOrchestratorMetrics(active_workflows=10)

        total = metrics.get_total_workflows()

        assert total == 10

    def test_get_total_workflows_return_type(self):
        """Test that get_total_workflows() returns integer."""
        metrics = ModelOrchestratorMetrics(
            active_workflows=1,
            completed_workflows=2,
            failed_workflows=3,
        )

        total = metrics.get_total_workflows()

        assert isinstance(total, int)
        assert total == 6


class TestModelOrchestratorMetricsGetSuccessRate:
    """Test get_success_rate() method."""

    def test_get_success_rate_with_no_failures(self):
        """Test get_success_rate() with 100% success."""
        metrics = ModelOrchestratorMetrics(completed_workflows=100, failed_workflows=0)

        success_rate = metrics.get_success_rate()

        assert success_rate == 100.0

    def test_get_success_rate_with_failures(self):
        """Test get_success_rate() with some failures."""
        metrics = ModelOrchestratorMetrics(completed_workflows=80, failed_workflows=20)

        success_rate = metrics.get_success_rate()

        assert success_rate == 80.0  # 80 / (80 + 20) * 100

    def test_get_success_rate_with_all_failures(self):
        """Test get_success_rate() with 0% success."""
        metrics = ModelOrchestratorMetrics(completed_workflows=0, failed_workflows=10)

        success_rate = metrics.get_success_rate()

        assert success_rate == 0.0

    def test_get_success_rate_with_no_completed_workflows(self):
        """Test get_success_rate() when no workflows completed or failed."""
        metrics = ModelOrchestratorMetrics(active_workflows=5)

        success_rate = metrics.get_success_rate()

        # When total is 0, return 0.0
        assert success_rate == 0.0

    def test_get_success_rate_ignores_active_workflows(self):
        """Test that get_success_rate() only considers completed and failed."""
        metrics = ModelOrchestratorMetrics(
            active_workflows=50,  # Should not affect calculation
            completed_workflows=90,
            failed_workflows=10,
        )

        success_rate = metrics.get_success_rate()

        assert success_rate == 90.0  # 90 / (90 + 10) * 100

    def test_get_success_rate_return_type(self):
        """Test that get_success_rate() returns float."""
        metrics = ModelOrchestratorMetrics(completed_workflows=75, failed_workflows=25)

        success_rate = metrics.get_success_rate()

        assert isinstance(success_rate, float)
        assert success_rate == 75.0

    def test_get_success_rate_with_decimal_result(self):
        """Test get_success_rate() with non-integer result."""
        metrics = ModelOrchestratorMetrics(completed_workflows=2, failed_workflows=1)

        success_rate = metrics.get_success_rate()

        # 2 / (2 + 1) * 100 = 66.666...
        assert 66.66 <= success_rate <= 66.67


class TestModelOrchestratorMetricsSerialization:
    """Test model serialization and deserialization."""

    def test_model_dump_basic(self):
        """Test model_dump() produces correct dictionary."""
        metrics = ModelOrchestratorMetrics(
            active_workflows=5,
            completed_workflows=100,
            failed_workflows=3,
            avg_execution_time_seconds=45.5,
            resource_utilization_percent=75.0,
        )

        dumped = metrics.model_dump()

        assert dumped["active_workflows"] == 5
        assert dumped["completed_workflows"] == 100
        assert dumped["failed_workflows"] == 3
        assert dumped["avg_execution_time_seconds"] == 45.5
        assert dumped["resource_utilization_percent"] == 75.0

    def test_model_dump_exclude_none(self):
        """Test model_dump(exclude_none=True) removes None fields."""
        metrics = ModelOrchestratorMetrics(active_workflows=10)

        dumped = metrics.model_dump(exclude_none=True)

        assert "active_workflows" in dumped
        assert "completed_workflows" in dumped  # Has default value 0
        assert "avg_execution_time_seconds" not in dumped  # None
        assert "resource_utilization_percent" not in dumped  # None

    def test_model_dump_json_roundtrip(self):
        """Test JSON serialization roundtrip."""
        original = ModelOrchestratorMetrics(
            active_workflows=5,
            completed_workflows=100,
            failed_workflows=3,
            avg_execution_time_seconds=45.5,
        )

        json_str = original.model_dump_json()
        restored = ModelOrchestratorMetrics.model_validate_json(json_str)

        assert restored.active_workflows == original.active_workflows
        assert restored.completed_workflows == original.completed_workflows
        assert restored.failed_workflows == original.failed_workflows
        assert (
            restored.avg_execution_time_seconds == original.avg_execution_time_seconds
        )


class TestModelOrchestratorMetricsComplexScenarios:
    """Test complex usage scenarios."""

    def test_high_load_scenario(self):
        """Test metrics for high load scenario."""
        metrics = ModelOrchestratorMetrics(
            active_workflows=500,
            completed_workflows=10000,
            failed_workflows=100,
            avg_execution_time_seconds=120.5,
            resource_utilization_percent=95.0,
        )

        assert metrics.get_total_workflows() == 10600
        assert 99.0 <= metrics.get_success_rate() <= 99.1  # ~99.01%
        assert metrics.resource_utilization_percent > 90.0

    def test_startup_scenario(self):
        """Test metrics for startup scenario (no history)."""
        metrics = ModelOrchestratorMetrics()

        assert metrics.get_total_workflows() == 0
        assert metrics.get_success_rate() == 0.0
        assert metrics.resource_utilization_percent is None

    def test_partial_failure_scenario(self):
        """Test metrics with significant failure rate."""
        metrics = ModelOrchestratorMetrics(
            active_workflows=10,
            completed_workflows=60,
            failed_workflows=40,
            avg_execution_time_seconds=30.0,
            resource_utilization_percent=50.0,
        )

        assert metrics.get_success_rate() == 60.0  # 60% success
        assert metrics.get_total_workflows() == 110


class TestModelOrchestratorMetricsEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_small_execution_time(self):
        """Test with very small execution time."""
        metrics = ModelOrchestratorMetrics(avg_execution_time_seconds=0.001)
        assert metrics.avg_execution_time_seconds == 0.001

    def test_very_large_workflow_counts(self):
        """Test with very large workflow counts."""
        metrics = ModelOrchestratorMetrics(
            active_workflows=1000000,
            completed_workflows=9999999,
            failed_workflows=1,
        )

        assert metrics.get_total_workflows() == 11000000
        # Success rate should be very high
        assert metrics.get_success_rate() > 99.99

    def test_resource_utilization_over_100_percent(self):
        """Test resource_utilization_percent can exceed 100% (overcommit)."""
        # Some orchestrators allow overcommitment
        metrics = ModelOrchestratorMetrics(resource_utilization_percent=150.0)
        assert metrics.resource_utilization_percent == 150.0


class TestModelOrchestratorMetricsTypeSafety:
    """Test type safety - ZERO TOLERANCE for Any types."""

    def test_no_any_types_in_annotations(self):
        """Test that model fields don't use Any type."""
        from typing import get_type_hints

        hints = get_type_hints(ModelOrchestratorMetrics)

        # Check that no field uses Any type
        for field_name, field_type in hints.items():
            type_str = str(field_type)
            assert (
                "typing.Any" not in type_str
            ), f"Field {field_name} uses Any type: {type_str}"

    def test_workflow_count_fields_are_integers(self):
        """Test that workflow count fields are properly typed as int."""
        from typing import get_type_hints

        hints = get_type_hints(ModelOrchestratorMetrics)

        assert hints["active_workflows"] == int
        assert hints["completed_workflows"] == int
        assert hints["failed_workflows"] == int

    def test_optional_float_fields_properly_typed(self):
        """Test that optional float fields are properly typed."""
        from typing import get_type_hints

        hints = get_type_hints(ModelOrchestratorMetrics)

        # These should be float | None
        assert "float" in str(hints["avg_execution_time_seconds"])
        assert "float" in str(hints["resource_utilization_percent"])
