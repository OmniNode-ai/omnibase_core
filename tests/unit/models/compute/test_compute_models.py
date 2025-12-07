"""Unit tests for Contract-Driven NodeCompute v1.0 compute models."""

import pytest
from pydantic import ValidationError
from uuid import uuid4

from omnibase_core.models.compute.model_compute_execution_context import (
    ModelComputeExecutionContext,
)
from omnibase_core.models.compute.model_compute_step_metadata import (
    ModelComputeStepMetadata,
)
from omnibase_core.models.compute.model_compute_step_result import (
    ModelComputeStepResult,
)
from omnibase_core.models.compute.model_compute_pipeline_result import (
    ModelComputePipelineResult,
)
from omnibase_core.models.model_compute_output import ModelComputeOutput


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelComputeExecutionContext:
    """Tests for ModelComputeExecutionContext."""

    def test_create_minimal(self) -> None:
        """Test creating context with minimal fields."""
        op_id = uuid4()
        context = ModelComputeExecutionContext(operation_id=op_id)
        assert context.operation_id == op_id
        assert context.correlation_id is None
        assert context.node_id is None

    def test_create_full(self) -> None:
        """Test creating context with all fields."""
        op_id = uuid4()
        corr_id = uuid4()
        context = ModelComputeExecutionContext(
            operation_id=op_id,
            correlation_id=corr_id,
            node_id="test-node-123",
        )
        assert context.operation_id == op_id
        assert context.correlation_id == corr_id
        assert context.node_id == "test-node-123"

    def test_is_frozen(self) -> None:
        """Test that model is immutable."""
        context = ModelComputeExecutionContext(operation_id=uuid4())
        with pytest.raises(ValidationError, match="frozen"):
            context.node_id = "modified"  # type: ignore[misc]

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelComputeExecutionContext(
                operation_id=uuid4(),
                extra_field="invalid",  # type: ignore[call-arg]
            )


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelComputeStepMetadata:
    """Tests for ModelComputeStepMetadata."""

    def test_create_minimal(self) -> None:
        """Test creating metadata with minimal fields."""
        metadata = ModelComputeStepMetadata(duration_ms=10.5)
        assert metadata.duration_ms == 10.5
        assert metadata.transformation_type is None

    def test_create_full(self) -> None:
        """Test creating metadata with all fields."""
        metadata = ModelComputeStepMetadata(
            duration_ms=25.3,
            transformation_type="case_conversion",
        )
        assert metadata.duration_ms == 25.3
        assert metadata.transformation_type == "case_conversion"

    def test_duration_ms_zero_allowed(self) -> None:
        """Test that zero duration is allowed."""
        metadata = ModelComputeStepMetadata(duration_ms=0.0)
        assert metadata.duration_ms == 0.0

    def test_duration_ms_negative_raises_error(self) -> None:
        """Test that negative duration raises validation error."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            ModelComputeStepMetadata(duration_ms=-1.0)

    def test_duration_ms_large_negative_raises_error(self) -> None:
        """Test that large negative duration raises validation error."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            ModelComputeStepMetadata(duration_ms=-999.99)

    def test_is_frozen(self) -> None:
        """Test that model is immutable."""
        metadata = ModelComputeStepMetadata(duration_ms=10.0)
        with pytest.raises(ValidationError, match="frozen"):
            metadata.duration_ms = 20.0  # type: ignore[misc]

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelComputeStepMetadata(
                duration_ms=10.0,
                extra_field="invalid",  # type: ignore[call-arg]
            )


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelComputeStepResult:
    """Tests for ModelComputeStepResult."""

    def test_create_success(self) -> None:
        """Test creating successful step result."""
        metadata = ModelComputeStepMetadata(duration_ms=5.0)
        result = ModelComputeStepResult(
            step_name="transform_case",
            output="HELLO WORLD",
            success=True,
            metadata=metadata,
        )
        assert result.step_name == "transform_case"
        assert result.output == "HELLO WORLD"
        assert result.success is True
        assert result.error_type is None
        assert result.error_message is None

    def test_create_failure(self) -> None:
        """Test creating failed step result."""
        metadata = ModelComputeStepMetadata(duration_ms=2.0)
        result = ModelComputeStepResult(
            step_name="validate_input",
            output=None,
            success=False,
            metadata=metadata,
            error_type="validation_error",
            error_message="Input schema validation failed",
        )
        assert result.success is False
        assert result.error_type == "validation_error"
        assert result.error_message == "Input schema validation failed"

    def test_is_frozen(self) -> None:
        """Test that model is immutable."""
        metadata = ModelComputeStepMetadata(duration_ms=5.0)
        result = ModelComputeStepResult(
            step_name="test",
            output="data",
            metadata=metadata,
        )
        with pytest.raises(ValidationError, match="frozen"):
            result.success = False  # type: ignore[misc]


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelComputePipelineResult:
    """Tests for ModelComputePipelineResult."""

    def test_create_success(self) -> None:
        """Test creating successful pipeline result."""
        metadata = ModelComputeStepMetadata(duration_ms=5.0)
        step_result = ModelComputeStepResult(
            step_name="step1",
            output="result",
            metadata=metadata,
        )

        result = ModelComputePipelineResult(
            success=True,
            output="final result",
            processing_time_ms=15.5,
            steps_executed=["step1"],
            step_results={"step1": step_result},
        )
        assert result.success is True
        assert result.output == "final result"
        assert result.processing_time_ms == 15.5
        assert result.steps_executed == ["step1"]
        assert "step1" in result.step_results
        assert result.error_type is None
        assert result.error_step is None

    def test_create_failure(self) -> None:
        """Test creating failed pipeline result."""
        metadata = ModelComputeStepMetadata(duration_ms=3.0)
        step_result = ModelComputeStepResult(
            step_name="failing_step",
            output=None,
            success=False,
            metadata=metadata,
            error_type="compute_error",
            error_message="Invalid input type",
        )

        result = ModelComputePipelineResult(
            success=False,
            output=None,
            processing_time_ms=3.5,
            steps_executed=["failing_step"],
            step_results={"failing_step": step_result},
            error_type="compute_error",
            error_message="Invalid input type",
            error_step="failing_step",
        )
        assert result.success is False
        assert result.error_step == "failing_step"

    def test_is_frozen(self) -> None:
        """Test that model is immutable."""
        result = ModelComputePipelineResult(
            success=True,
            output="data",
            processing_time_ms=10.0,
            steps_executed=[],
            step_results={},
        )
        with pytest.raises(ValidationError, match="frozen"):
            result.success = False  # type: ignore[misc]

    def test_processing_time_ms_zero_allowed(self) -> None:
        """Test that zero processing time is allowed."""
        result = ModelComputePipelineResult(
            success=True,
            output="data",
            processing_time_ms=0.0,
            steps_executed=[],
            step_results={},
        )
        assert result.processing_time_ms == 0.0

    def test_processing_time_ms_negative_raises_error(self) -> None:
        """Test that negative processing time raises validation error."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            ModelComputePipelineResult(
                success=True,
                output="data",
                processing_time_ms=-1.0,
                steps_executed=[],
                step_results={},
            )

    def test_processing_time_ms_large_negative_raises_error(self) -> None:
        """Test that large negative processing time raises validation error."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            ModelComputePipelineResult(
                success=True,
                output="data",
                processing_time_ms=-999.99,
                steps_executed=[],
                step_results={},
            )

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelComputePipelineResult(
                success=True,
                output="data",
                processing_time_ms=10.0,
                steps_executed=[],
                step_results={},
                extra_field="invalid",  # type: ignore[call-arg]
            )


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestModelComputeOutput:
    """Tests for ModelComputeOutput."""

    def test_create_minimal(self) -> None:
        """Test creating output with minimal fields."""
        op_id = uuid4()
        output = ModelComputeOutput(
            result="test_result",
            operation_id=op_id,
            computation_type="test_computation",
            processing_time_ms=10.5,
        )
        assert output.result == "test_result"
        assert output.operation_id == op_id
        assert output.computation_type == "test_computation"
        assert output.processing_time_ms == 10.5
        assert output.cache_hit is False
        assert output.parallel_execution_used is False
        assert output.metadata == {}

    def test_create_full(self) -> None:
        """Test creating output with all fields."""
        op_id = uuid4()
        output = ModelComputeOutput(
            result={"transformed": "data"},
            operation_id=op_id,
            computation_type="complex_transform",
            processing_time_ms=25.3,
            cache_hit=True,
            parallel_execution_used=True,
            metadata={"source": "test"},
        )
        assert output.result == {"transformed": "data"}
        assert output.cache_hit is True
        assert output.parallel_execution_used is True
        assert output.metadata == {"source": "test"}

    def test_processing_time_ms_zero_allowed(self) -> None:
        """Test that zero processing time is allowed (e.g., cache hit)."""
        output = ModelComputeOutput(
            result="cached",
            operation_id=uuid4(),
            computation_type="test",
            processing_time_ms=0.0,
            cache_hit=True,
        )
        assert output.processing_time_ms == 0.0

    def test_processing_time_ms_negative_raises_error(self) -> None:
        """Test that negative processing time raises validation error."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            ModelComputeOutput(
                result="test",
                operation_id=uuid4(),
                computation_type="test",
                processing_time_ms=-1.0,
            )

    def test_processing_time_ms_large_negative_raises_error(self) -> None:
        """Test that large negative processing time raises validation error."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            ModelComputeOutput(
                result="test",
                operation_id=uuid4(),
                computation_type="test",
                processing_time_ms=-999.99,
            )

    def test_is_frozen(self) -> None:
        """Test that model is immutable."""
        output = ModelComputeOutput(
            result="test",
            operation_id=uuid4(),
            computation_type="test",
            processing_time_ms=10.0,
        )
        with pytest.raises(ValidationError, match="frozen"):
            output.result = "modified"  # type: ignore[misc]

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelComputeOutput(
                result="test",
                operation_id=uuid4(),
                computation_type="test",
                processing_time_ms=10.0,
                extra_field="invalid",  # type: ignore[call-arg]
            )
