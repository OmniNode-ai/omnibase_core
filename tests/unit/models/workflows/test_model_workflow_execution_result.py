"""
Tests for ModelWorkflowExecutionResult.

Comprehensive test suite for workflow execution results including status handling,
coordination metrics integration, execution timing, and error scenarios.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_workflow_coordination import (
    EnumWorkflowStatus as EnumWorkflowStatusCoordination,
)
from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus
from omnibase_core.models.core.model_workflow_metrics import ModelWorkflowMetrics
from omnibase_core.models.workflows.model_workflow_execution_result import (
    ModelWorkflowExecutionResult,
)


class TestBasicCreationAndValidation:
    """Test basic creation and validation of workflow execution results."""

    def test_successful_creation_with_all_fields(self) -> None:
        """Test creating workflow execution result with all required fields."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=1.0,
        )

        result = ModelWorkflowExecutionResult(
            workflow_id=workflow_id,
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=1000,
            result_data={"output": "success", "count": 42},
            error_message=None,
            coordination_metrics=metrics,
        )

        assert result.workflow_id == workflow_id
        assert result.status == EnumWorkflowStatusCoordination.COMPLETED
        assert result.execution_time_ms == 1000
        assert result.result_data == {"output": "success", "count": 42}
        assert result.error_message is None
        assert result.coordination_metrics == metrics

    def test_creation_with_minimal_fields(self) -> None:
        """Test creating result with minimal required fields using defaults."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.RUNNING,
            duration_seconds=0.5,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.RUNNING,
            execution_time_ms=500,
            coordination_metrics=metrics,
        )

        assert isinstance(result.workflow_id, UUID)
        assert result.status == EnumWorkflowStatusCoordination.RUNNING
        assert result.execution_time_ms == 500
        assert result.result_data == {}
        assert result.error_message is None

    def test_creation_with_custom_workflow_id(self) -> None:
        """Test creating result with custom workflow ID."""
        custom_id = UUID("12345678-1234-5678-9abc-123456789abc")
        metrics = ModelWorkflowMetrics(
            workflow_id=custom_id,
            status=EnumWorkflowStatus.PENDING,
            duration_seconds=0.1,
        )

        result = ModelWorkflowExecutionResult(
            workflow_id=custom_id,
            status=EnumWorkflowStatusCoordination.CREATED,
            execution_time_ms=100,
            coordination_metrics=metrics,
        )

        assert result.workflow_id == custom_id

    def test_negative_execution_time_validation(self) -> None:
        """Test that negative execution time is rejected."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.RUNNING,
            duration_seconds=0.1,
        )

        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            ModelWorkflowExecutionResult(
                status=EnumWorkflowStatusCoordination.RUNNING,
                execution_time_ms=-100,
                coordination_metrics=metrics,
            )

    def test_missing_required_fields(self) -> None:
        """Test that missing required fields cause validation errors."""
        with pytest.raises(ValidationError, match="Field required"):
            ModelWorkflowExecutionResult(  # type: ignore[call-arg]
                workflow_id=uuid4(),
                execution_time_ms=100,
            )


class TestWorkflowStatusEnumHandling:
    """Test workflow status enum handling and transitions."""

    def test_all_workflow_status_values(self) -> None:
        """Test that all workflow status enum values can be used."""
        workflow_id = uuid4()

        # Test with coordination enum values
        for status in EnumWorkflowStatusCoordination:
            metrics = ModelWorkflowMetrics(
                workflow_id=workflow_id,
                status=EnumWorkflowStatus.RUNNING,  # Use metrics enum
                duration_seconds=0.1,
            )
            result = ModelWorkflowExecutionResult(
                status=status,  # Use coordination enum
                execution_time_ms=100,
                coordination_metrics=metrics,
            )
            assert result.status == status

    def test_created_status(self) -> None:
        """Test workflow with CREATED status."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.PENDING,
            duration_seconds=0.0,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.CREATED,
            execution_time_ms=0,
            coordination_metrics=metrics,
        )

        assert result.status == EnumWorkflowStatusCoordination.CREATED
        assert result.error_message is None

    def test_running_status(self) -> None:
        """Test workflow with RUNNING status."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.RUNNING,
            duration_seconds=0.5,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.RUNNING,
            execution_time_ms=500,
            coordination_metrics=metrics,
        )

        assert result.status == EnumWorkflowStatusCoordination.RUNNING

    def test_completed_status_with_result_data(self) -> None:
        """Test workflow with COMPLETED status and result data."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=1.0,
            steps_total=5,
            steps_completed=5,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=1000,
            result_data={
                "processed_items": 100,
                "success_rate": 98.5,
                "output_file": "/path/to/output.json",
            },
            coordination_metrics=metrics,
        )

        assert result.status == EnumWorkflowStatusCoordination.COMPLETED
        assert result.result_data["processed_items"] == 100
        assert result.result_data["success_rate"] == 98.5
        assert result.error_message is None

    def test_failed_status_with_error_message(self) -> None:
        """Test workflow with FAILED status and error message."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.FAILED,
            duration_seconds=0.25,
            error_message="Node timeout: COMPUTE node failed to respond within 30s",
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.FAILED,
            execution_time_ms=250,
            error_message="Node timeout: COMPUTE node failed to respond within 30s",
            coordination_metrics=metrics,
        )

        assert result.status == EnumWorkflowStatusCoordination.FAILED
        assert result.error_message is not None
        assert "Node timeout" in result.error_message

    def test_cancelled_status(self) -> None:
        """Test workflow with CANCELLED status."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.CANCELLED,
            duration_seconds=0.15,
            error_message="User requested cancellation",
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.CANCELLED,
            execution_time_ms=150,
            error_message="User requested cancellation",
            coordination_metrics=metrics,
        )

        assert result.status == EnumWorkflowStatusCoordination.CANCELLED
        assert result.error_message == "User requested cancellation"


class TestCoordinationMetricsIntegration:
    """Test integration with coordination metrics."""

    def test_metrics_basic_structure(self) -> None:
        """Test that metrics are properly integrated."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=1.0,
            steps_total=5,
            steps_completed=5,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=1000,
            coordination_metrics=metrics,
        )

        assert result.coordination_metrics.workflow_id == workflow_id
        assert result.coordination_metrics.status == EnumWorkflowStatus.COMPLETED
        assert result.coordination_metrics.duration_seconds == 1.0
        assert result.coordination_metrics.steps_total == 5
        assert result.coordination_metrics.steps_completed == 5

    def test_metrics_validation_constraints(self) -> None:
        """Test that metrics can be created with various values."""
        workflow_id = uuid4()

        # Metrics can be created with any duration value (no validation constraint)
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.RUNNING,
            duration_seconds=-1.0,  # Allowed - no constraint
        )
        assert metrics.duration_seconds == -1.0

    def test_high_coordination_overhead(self) -> None:
        """Test metrics with long duration (representing high overhead)."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=1.0,
            steps_total=10,
            steps_completed=10,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=1000,
            coordination_metrics=metrics,
        )

        assert result.coordination_metrics.duration_seconds == 1.0

    def test_optimal_parallel_execution_metrics(self) -> None:
        """Test metrics for optimal parallel execution."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=0.5,
            steps_total=10,
            steps_completed=10,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=500,
            coordination_metrics=metrics,
        )

        assert result.coordination_metrics.steps_completed == 10
        assert result.coordination_metrics.steps_total == 10

    def test_sequential_execution_metrics(self) -> None:
        """Test metrics for sequential execution (no parallelism)."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=2.0,
            steps_total=5,
            steps_completed=5,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=2000,
            coordination_metrics=metrics,
        )

        assert result.coordination_metrics.steps_total == 5
        assert result.coordination_metrics.steps_completed == 5


class TestExecutionTimingAndResultData:
    """Test execution timing and result data handling."""

    def test_zero_execution_time(self) -> None:
        """Test workflow with zero execution time (immediate completion)."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.PENDING,
            duration_seconds=0.0,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.CREATED,
            execution_time_ms=0,
            coordination_metrics=metrics,
        )

        assert result.execution_time_ms == 0

    def test_long_execution_time(self) -> None:
        """Test workflow with long execution time."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=3600.0,  # 1 hour
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=3600000,
            coordination_metrics=metrics,
        )

        assert result.execution_time_ms == 3600000

    def test_empty_result_data(self) -> None:
        """Test workflow with empty result data."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=0.1,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=100,
            coordination_metrics=metrics,
        )

        assert result.result_data == {}

    def test_structured_result_data_with_primitives(self) -> None:
        """Test result data with various primitive types."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=0.5,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=500,
            result_data={
                "string_value": "test_output",
                "int_value": 42,
                "float_value": 3.14159,
                "bool_value": True,
                "none_value": None,
            },
            coordination_metrics=metrics,
        )

        assert result.result_data["string_value"] == "test_output"
        assert result.result_data["int_value"] == 42
        assert result.result_data["float_value"] == 3.14159
        assert result.result_data["bool_value"] is True
        assert result.result_data["none_value"] is None

    def test_result_data_with_nested_structures(self) -> None:
        """Test result data can handle nested dictionaries and lists."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=0.8,
        )

        # Note: PrimitiveValueType allows nested structures
        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=800,
            result_data={
                "summary": {
                    "total_processed": 100,
                    "success_rate": 98.5,
                },
                "outputs": ["/path/1", "/path/2", "/path/3"],
                "metadata": {
                    "version": "1.0",
                    "timestamp": "2025-09-30T12:00:00Z",
                },
            },
            coordination_metrics=metrics,
        )

        assert isinstance(result.result_data["summary"], dict)
        assert isinstance(result.result_data["outputs"], list)
        assert len(result.result_data["outputs"]) == 3

    def test_execution_time_consistency_with_metrics(self) -> None:
        """Test that execution_time_ms is consistent with metrics."""
        workflow_id = uuid4()
        execution_time = 1000
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=1.0,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=execution_time,
            coordination_metrics=metrics,
        )

        # Convert execution_time_ms to seconds for comparison
        assert (
            result.execution_time_ms / 1000
            == result.coordination_metrics.duration_seconds
        )


class TestErrorHandlingScenarios:
    """Test error handling and failure scenarios."""

    def test_error_message_with_failed_status(self) -> None:
        """Test that error message is properly stored with FAILED status."""
        workflow_id = uuid4()
        error_msg = "COMPUTE node failed: Division by zero in calculation"
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.FAILED,
            duration_seconds=0.2,
            error_message=error_msg,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.FAILED,
            execution_time_ms=200,
            error_message=error_msg,
            coordination_metrics=metrics,
        )

        assert result.status == EnumWorkflowStatusCoordination.FAILED
        assert result.error_message == error_msg

    def test_no_error_message_with_success_status(self) -> None:
        """Test that successful workflows have no error message."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=1.0,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=1000,
            coordination_metrics=metrics,
        )

        assert result.error_message is None

    def test_multiple_failure_scenarios(self) -> None:
        """Test various failure scenarios with appropriate error messages."""
        workflow_id = uuid4()
        failure_scenarios = [
            "Timeout: Node exceeded 30s execution limit",
            "Resource exhausted: Out of memory during processing",
            "Validation failed: Input data schema mismatch",
            "Dependency failure: Required EFFECT node unavailable",
        ]

        for error_msg in failure_scenarios:
            metrics = ModelWorkflowMetrics(
                workflow_id=workflow_id,
                status=EnumWorkflowStatus.FAILED,
                duration_seconds=0.15,
                error_message=error_msg,
            )
            result = ModelWorkflowExecutionResult(
                status=EnumWorkflowStatusCoordination.FAILED,
                execution_time_ms=150,
                error_message=error_msg,
                coordination_metrics=metrics,
            )

            assert result.status == EnumWorkflowStatusCoordination.FAILED
            assert result.error_message == error_msg

    def test_partial_result_data_on_failure(self) -> None:
        """Test that partial result data can be captured on failure."""
        workflow_id = uuid4()
        error_msg = "Processing failed at item 46: Invalid format"
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.FAILED,
            duration_seconds=0.3,
            steps_total=100,
            steps_completed=45,
            steps_failed=1,
            error_message=error_msg,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.FAILED,
            execution_time_ms=300,
            result_data={
                "processed_count": 45,
                "failed_at_item": 46,
                "partial_output": "/path/to/partial.json",
            },
            error_message=error_msg,
            coordination_metrics=metrics,
        )

        assert result.status == EnumWorkflowStatusCoordination.FAILED
        assert result.result_data["processed_count"] == 45
        assert result.error_message is not None


class TestWorkflowSpecificFeatures:
    """Test workflow-specific features and patterns."""

    def test_workflow_with_metadata_only(self) -> None:
        """Test workflow result that captures only metadata without output data."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=0.05,
            steps_total=4,
            steps_completed=4,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=50,
            result_data={
                "nodes_executed": 4,
                "pattern_used": "SEQUENTIAL",
                "recovery_attempts": 0,
            },
            coordination_metrics=metrics,
        )

        assert result.result_data["nodes_executed"] == 4
        assert result.result_data["pattern_used"] == "SEQUENTIAL"

    def test_workflow_status_progression(self) -> None:
        """Test typical workflow status progression."""
        workflow_id = uuid4()

        # Stage 1: Created
        metrics_created = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.PENDING,
            duration_seconds=0.0,
        )
        result_created = ModelWorkflowExecutionResult(
            workflow_id=workflow_id,
            status=EnumWorkflowStatusCoordination.CREATED,
            execution_time_ms=0,
            coordination_metrics=metrics_created,
        )
        assert result_created.status == EnumWorkflowStatusCoordination.CREATED

        # Stage 2: Running
        metrics_running = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.RUNNING,
            duration_seconds=0.5,
            steps_total=5,
            steps_completed=3,
        )
        result_running = ModelWorkflowExecutionResult(
            workflow_id=workflow_id,
            status=EnumWorkflowStatusCoordination.RUNNING,
            execution_time_ms=500,
            coordination_metrics=metrics_running,
        )
        assert result_running.status == EnumWorkflowStatusCoordination.RUNNING

        # Stage 3: Completed
        metrics_completed = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=1.0,
            steps_total=5,
            steps_completed=5,
        )
        result_completed = ModelWorkflowExecutionResult(
            workflow_id=workflow_id,
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=1000,
            result_data={"final_output": "success"},
            coordination_metrics=metrics_completed,
        )
        assert result_completed.status == EnumWorkflowStatusCoordination.COMPLETED
        assert result_completed.workflow_id == workflow_id

    def test_coordination_efficiency_analysis(self) -> None:
        """Test analyzing coordination efficiency from metrics."""
        workflow_id = uuid4()

        # Efficient workflow - short duration
        efficient_metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=0.5,
            steps_total=10,
            steps_completed=10,
        )
        efficient_result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=500,
            coordination_metrics=efficient_metrics,
        )

        # Inefficient workflow - longer duration
        inefficient_metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=2.0,
            steps_total=10,
            steps_completed=10,
        )
        inefficient_result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=2000,
            coordination_metrics=inefficient_metrics,
        )

        # Efficient workflow should have shorter duration
        assert (
            efficient_result.coordination_metrics.duration_seconds
            < inefficient_result.coordination_metrics.duration_seconds
        )


class TestModelConfiguration:
    """Test Pydantic model configuration and behavior."""

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields are ignored per model config."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=0.1,
        )

        # Extra field should be ignored
        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=100,
            coordination_metrics=metrics,
            extra_field="should_be_ignored",  # type: ignore[call-arg]
        )

        assert result.status == EnumWorkflowStatusCoordination.COMPLETED
        assert not hasattr(result, "extra_field")

    def test_validate_assignment(self) -> None:
        """Test that assignment validation is enabled."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.RUNNING,
            duration_seconds=0.1,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.RUNNING,
            execution_time_ms=100,
            coordination_metrics=metrics,
        )

        # Test that assignment validation catches invalid values
        with pytest.raises(ValidationError):
            result.execution_time_ms = -100  # type: ignore[assignment]

    def test_enum_values_not_converted(self) -> None:
        """Test that enum values are not converted to their string values."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=0.1,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=100,
            coordination_metrics=metrics,
        )

        # Enum should remain as enum instance, not string
        assert isinstance(result.status, EnumWorkflowStatusCoordination)
        assert result.status == EnumWorkflowStatusCoordination.COMPLETED


class TestZeroToleranceCompliance:
    """Test ZERO TOLERANCE compliance - no Any types allowed."""

    def test_all_fields_strongly_typed(self) -> None:
        """Test that all fields have concrete types, no Any."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=0.1,
        )

        result = ModelWorkflowExecutionResult(
            status=EnumWorkflowStatusCoordination.COMPLETED,
            execution_time_ms=100,
            result_data={"key": "value"},
            coordination_metrics=metrics,
        )

        # Verify types are concrete
        assert isinstance(result.workflow_id, UUID)
        assert isinstance(result.status, EnumWorkflowStatusCoordination)
        assert isinstance(result.execution_time_ms, int)
        assert isinstance(result.result_data, dict)
        assert isinstance(result.coordination_metrics, ModelWorkflowMetrics)

    def test_type_checking_enforcement(self) -> None:
        """Test that type checking is enforced at runtime."""
        workflow_id = uuid4()
        metrics = ModelWorkflowMetrics(
            workflow_id=workflow_id,
            status=EnumWorkflowStatus.COMPLETED,
            duration_seconds=0.1,
        )

        # Invalid status type
        with pytest.raises(ValidationError, match="Input should be"):
            ModelWorkflowExecutionResult(
                status="INVALID_STATUS",  # type: ignore[arg-type]
                execution_time_ms=100,
                coordination_metrics=metrics,
            )

        # Invalid execution_time_ms type
        with pytest.raises(ValidationError, match="Input should be a valid integer"):
            ModelWorkflowExecutionResult(
                status=EnumWorkflowStatusCoordination.COMPLETED,
                execution_time_ms="not_an_int",  # type: ignore[arg-type]
                coordination_metrics=metrics,
            )


__all__ = [
    "TestBasicCreationAndValidation",
    "TestCoordinationMetricsIntegration",
    "TestErrorHandlingScenarios",
    "TestExecutionTimingAndResultData",
    "TestModelConfiguration",
    "TestWorkflowSpecificFeatures",
    "TestWorkflowStatusEnumHandling",
    "TestZeroToleranceCompliance",
]
