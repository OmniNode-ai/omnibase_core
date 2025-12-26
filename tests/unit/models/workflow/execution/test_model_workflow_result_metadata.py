"""Tests for ModelWorkflowResultMetadata.

Tests the production model at:
src/omnibase_core/models/workflow/execution/model_workflow_result_metadata.py
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.workflow.execution.model_workflow_result_metadata import (
    ModelWorkflowResultMetadata,
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

    def test_workflow_hash_valid_64_char_hex_lowercase(self) -> None:
        """Test that valid 64-char lowercase hex hash is accepted."""
        valid_hash = "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"
        metadata = ModelWorkflowResultMetadata(
            execution_mode="sequential",
            workflow_name="test",
            workflow_hash=valid_hash,
        )
        assert metadata.workflow_hash == valid_hash

    def test_workflow_hash_valid_64_char_hex_uppercase(self) -> None:
        """Test that valid 64-char uppercase hex hash is accepted."""
        valid_hash = "A1B2C3D4E5F6789012345678901234567890ABCDEF1234567890ABCDEF123456"
        metadata = ModelWorkflowResultMetadata(
            execution_mode="sequential",
            workflow_name="test",
            workflow_hash=valid_hash,
        )
        assert metadata.workflow_hash == valid_hash

    def test_workflow_hash_valid_64_char_hex_mixed_case(self) -> None:
        """Test that valid 64-char mixed case hex hash is accepted."""
        valid_hash = "a1B2c3D4e5F6789012345678901234567890AbCdEf1234567890aBcDeF123456"
        metadata = ModelWorkflowResultMetadata(
            execution_mode="sequential",
            workflow_name="test",
            workflow_hash=valid_hash,
        )
        assert metadata.workflow_hash == valid_hash

    def test_workflow_hash_empty_string_allowed(self) -> None:
        """Test that empty string is allowed as default."""
        metadata = ModelWorkflowResultMetadata(
            execution_mode="sequential",
            workflow_name="test",
            workflow_hash="",
        )
        assert metadata.workflow_hash == ""

    def test_workflow_hash_invalid_too_short(self) -> None:
        """Test that hash shorter than 64 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowResultMetadata(
                execution_mode="sequential",
                workflow_name="test",
                workflow_hash="a1b2c3d4",  # Only 8 chars
            )
        error_str = str(exc_info.value)
        assert "workflow_hash" in error_str

    def test_workflow_hash_invalid_too_long(self) -> None:
        """Test that hash longer than 64 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowResultMetadata(
                execution_mode="sequential",
                workflow_name="test",
                workflow_hash="a" * 65,  # 65 chars
            )
        error_str = str(exc_info.value)
        assert "workflow_hash" in error_str

    def test_workflow_hash_invalid_non_hex_characters(self) -> None:
        """Test that non-hex characters are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowResultMetadata(
                execution_mode="sequential",
                workflow_name="test",
                # 'g' and 'z' are not valid hex characters
                workflow_hash="g1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdefz23456",
            )
        error_str = str(exc_info.value)
        assert "workflow_hash" in error_str

    def test_workflow_hash_invalid_special_characters(self) -> None:
        """Test that special characters are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowResultMetadata(
                execution_mode="sequential",
                workflow_name="test",
                workflow_hash="a1b2c3d4-5f67-8901-2345-678901234567890abcdef1234567890ab",
            )
        error_str = str(exc_info.value)
        assert "workflow_hash" in error_str

    def test_workflow_hash_invalid_whitespace(self) -> None:
        """Test that whitespace is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowResultMetadata(
                execution_mode="sequential",
                workflow_name="test",
                workflow_hash=" " * 64,  # 64 spaces
            )
        error_str = str(exc_info.value)
        assert "workflow_hash" in error_str
