"""Unit tests for ModelComputeSubcontract validation."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_compute_step_type import EnumComputeStepType
from omnibase_core.enums.enum_transformation_type import EnumTransformationType
from omnibase_core.models.contracts.subcontracts.model_compute_pipeline_step import (
    ModelComputePipelineStep,
)
from omnibase_core.models.contracts.subcontracts.model_compute_subcontract import (
    ModelComputeSubcontract,
)


@pytest.mark.unit
class TestModelComputeSubcontractCreation:
    """Tests for ModelComputeSubcontract creation."""

    def test_create_minimal(self) -> None:
        """Test creating subcontract with minimal fields."""
        subcontract = ModelComputeSubcontract(
            operation_name="test_op",
            operation_version="1.0.0",
            pipeline=[],
        )
        assert subcontract.operation_name == "test_op"
        assert subcontract.operation_version == "1.0.0"
        assert subcontract.pipeline == []
        assert subcontract.pipeline_timeout_ms is None
        assert subcontract.version == "1.0.0"

    def test_create_with_pipeline(self) -> None:
        """Test creating subcontract with pipeline steps."""
        step = ModelComputePipelineStep(
            step_name="transform",
            step_type=EnumComputeStepType.TRANSFORMATION,
            transformation_type=EnumTransformationType.IDENTITY,
        )
        subcontract = ModelComputeSubcontract(
            operation_name="test_op",
            operation_version="1.0.0",
            pipeline=[step],
        )
        assert len(subcontract.pipeline) == 1
        assert subcontract.pipeline[0].step_name == "transform"

    def test_create_with_timeout(self) -> None:
        """Test creating subcontract with pipeline timeout."""
        subcontract = ModelComputeSubcontract(
            operation_name="test_op",
            operation_version="1.0.0",
            pipeline=[],
            pipeline_timeout_ms=5000,
        )
        assert subcontract.pipeline_timeout_ms == 5000


@pytest.mark.unit
class TestModelComputeSubcontractTimeoutValidation:
    """Tests for pipeline_timeout_ms validation."""

    def test_timeout_none_allowed(self) -> None:
        """Test that None timeout is allowed (no timeout)."""
        subcontract = ModelComputeSubcontract(
            operation_name="test_op",
            operation_version="1.0.0",
            pipeline=[],
            pipeline_timeout_ms=None,
        )
        assert subcontract.pipeline_timeout_ms is None

    def test_timeout_positive_allowed(self) -> None:
        """Test that positive timeout values are allowed."""
        subcontract = ModelComputeSubcontract(
            operation_name="test_op",
            operation_version="1.0.0",
            pipeline=[],
            pipeline_timeout_ms=1000,
        )
        assert subcontract.pipeline_timeout_ms == 1000

    def test_timeout_large_value_allowed(self) -> None:
        """Test that large timeout values are allowed (up to 1 hour)."""
        subcontract = ModelComputeSubcontract(
            operation_name="test_op",
            operation_version="1.0.0",
            pipeline=[],
            pipeline_timeout_ms=600000,  # 10 minutes
        )
        assert subcontract.pipeline_timeout_ms == 600000

    def test_timeout_max_allowed(self) -> None:
        """Test that maximum timeout (1 hour) is allowed."""
        subcontract = ModelComputeSubcontract(
            operation_name="test_op",
            operation_version="1.0.0",
            pipeline=[],
            pipeline_timeout_ms=3600000,  # 1 hour (max allowed)
        )
        assert subcontract.pipeline_timeout_ms == 3600000

    def test_timeout_exceeds_max_raises_error(self) -> None:
        """Test that timeout exceeding 1 hour raises validation error."""
        with pytest.raises(ValidationError, match="less than or equal to 3600000"):
            ModelComputeSubcontract(
                operation_name="test_op",
                operation_version="1.0.0",
                pipeline=[],
                pipeline_timeout_ms=3600001,  # Just over 1 hour
            )

    def test_timeout_one_allowed(self) -> None:
        """Test that timeout of 1ms is allowed."""
        subcontract = ModelComputeSubcontract(
            operation_name="test_op",
            operation_version="1.0.0",
            pipeline=[],
            pipeline_timeout_ms=1,
        )
        assert subcontract.pipeline_timeout_ms == 1

    def test_timeout_zero_raises_error(self) -> None:
        """Test that zero timeout raises validation error."""
        with pytest.raises(ValidationError, match="greater than 0"):
            ModelComputeSubcontract(
                operation_name="test_op",
                operation_version="1.0.0",
                pipeline=[],
                pipeline_timeout_ms=0,
            )

    def test_timeout_negative_raises_error(self) -> None:
        """Test that negative timeout raises validation error."""
        with pytest.raises(ValidationError, match="greater than 0"):
            ModelComputeSubcontract(
                operation_name="test_op",
                operation_version="1.0.0",
                pipeline=[],
                pipeline_timeout_ms=-1000,
            )

    def test_timeout_large_negative_raises_error(self) -> None:
        """Test that large negative timeout raises validation error."""
        with pytest.raises(ValidationError, match="greater than 0"):
            ModelComputeSubcontract(
                operation_name="test_op",
                operation_version="1.0.0",
                pipeline=[],
                pipeline_timeout_ms=-99999,
            )


@pytest.mark.unit
class TestModelComputeSubcontractFrozen:
    """Tests for model immutability."""

    def test_is_frozen(self) -> None:
        """Test that model is immutable."""
        subcontract = ModelComputeSubcontract(
            operation_name="test_op",
            operation_version="1.0.0",
            pipeline=[],
        )
        with pytest.raises(ValidationError):
            subcontract.operation_name = "modified"  # type: ignore[misc]

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelComputeSubcontract(
                operation_name="test_op",
                operation_version="1.0.0",
                pipeline=[],
                extra_field="invalid",  # type: ignore[call-arg]
            )
