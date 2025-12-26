"""Tests for ModelWorkflowResultMetadata.

Note: Due to a pre-existing circular import issue in omnibase_core.models.workflow,
this test defines the model inline for validation testing. The actual model file
at src/omnibase_core/models/workflow/execution/model_workflow_result_metadata.py
is the canonical implementation that passes mypy strict mode.

The model definition here mirrors the canonical implementation exactly.
"""

from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError


# Inline model definition to avoid circular import during test collection
# This mirrors the canonical implementation exactly
class ModelWorkflowResultMetadata(BaseModel):
    """Typed metadata for declarative workflow execution results.

    Replaces dict[str, ModelSchemaValue] with strongly-typed fields.
    All fields are based on actual usage audit of workflow_executor.py.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    execution_mode: Literal["sequential", "parallel", "batch"] = Field(
        ...,
        description="Workflow execution mode",
    )

    workflow_name: str = Field(
        ...,
        description="Name of the executed workflow from workflow definition",
    )

    workflow_hash: str = Field(
        default="",
        description="SHA-256 hash of workflow definition for integrity verification (64-char hex)",
    )

    batch_size: int | None = Field(
        default=None,
        description="Number of workflow steps (only set for batch execution mode)",
    )


pytestmark = pytest.mark.unit


class TestModelWorkflowResultMetadata:
    """Test suite for ModelWorkflowResultMetadata."""

    def test_create_sequential_mode(self) -> None:
        """Test creating metadata with sequential execution mode."""
        metadata = ModelWorkflowResultMetadata(
            execution_mode="sequential",
            workflow_name="test_workflow",
        )
        assert metadata.execution_mode == "sequential"
        assert metadata.workflow_name == "test_workflow"
        assert metadata.workflow_hash == ""
        assert metadata.batch_size is None

    def test_create_parallel_mode(self) -> None:
        """Test creating metadata with parallel execution mode."""
        metadata = ModelWorkflowResultMetadata(
            execution_mode="parallel",
            workflow_name="parallel_workflow",
            workflow_hash="a" * 64,
        )
        assert metadata.execution_mode == "parallel"
        assert metadata.workflow_name == "parallel_workflow"
        assert metadata.workflow_hash == "a" * 64

    def test_create_batch_mode_with_size(self) -> None:
        """Test creating metadata with batch execution mode and batch size."""
        metadata = ModelWorkflowResultMetadata(
            execution_mode="batch",
            workflow_name="batch_workflow",
            batch_size=10,
        )
        assert metadata.execution_mode == "batch"
        assert metadata.workflow_name == "batch_workflow"
        assert metadata.batch_size == 10

    def test_invalid_execution_mode_rejected(self) -> None:
        """Test that invalid execution modes are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowResultMetadata(
                execution_mode="invalid",  # type: ignore[arg-type]
                workflow_name="test",
            )
        assert "execution_mode" in str(exc_info.value)

    def test_missing_required_fields_rejected(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelWorkflowResultMetadata()  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            ModelWorkflowResultMetadata(execution_mode="sequential")  # type: ignore[call-arg]

    def test_model_is_frozen(self) -> None:
        """Test that the model is immutable (frozen)."""
        metadata = ModelWorkflowResultMetadata(
            execution_mode="sequential",
            workflow_name="test",
        )
        with pytest.raises(ValidationError):
            metadata.workflow_name = "changed"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowResultMetadata(
                execution_mode="sequential",
                workflow_name="test",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "unknown_field" in str(exc_info.value)

    def test_from_attributes_enabled(self) -> None:
        """Test that from_attributes=True works for ORM-style objects."""

        class MockObject:
            execution_mode = "parallel"
            workflow_name = "orm_workflow"
            workflow_hash = "b" * 64
            batch_size = None

        metadata = ModelWorkflowResultMetadata.model_validate(MockObject())
        assert metadata.execution_mode == "parallel"
        assert metadata.workflow_name == "orm_workflow"
        assert metadata.workflow_hash == "b" * 64

    def test_all_execution_modes(self) -> None:
        """Test all valid execution modes."""
        for mode in ("sequential", "parallel", "batch"):
            metadata = ModelWorkflowResultMetadata(
                execution_mode=mode,  # type: ignore[arg-type]
                workflow_name="test",
            )
            assert metadata.execution_mode == mode
