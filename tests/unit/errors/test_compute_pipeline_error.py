"""
Tests for ComputePipelineError (OMN-465).

TDD tests for compute pipeline error class used in contract-driven NodeCompute v1.0.
"""

from uuid import UUID, uuid4

import pytest


@pytest.mark.timeout(10)
class TestComputePipelineError:
    """Tests for ComputePipelineError."""

    def test_compute_pipeline_error_creation(self) -> None:
        """Test creating ComputePipelineError with minimal args."""
        from omnibase_core.errors.exception_compute_pipeline_error import (
            ComputePipelineError,
        )

        error = ComputePipelineError("Pipeline step failed")

        # ModelOnexError includes error code in string representation
        assert "[ONEX_CORE_165_PROCESSING_ERROR]" in str(error)
        assert "Pipeline step failed" in str(error)
        # Check error-specific attributes before isinstance check
        assert error.correlation_id is not None
        assert isinstance(error.correlation_id, UUID)
        assert isinstance(error, Exception)

    def test_compute_pipeline_error_with_step_name(self) -> None:
        """Test ComputePipelineError with step_name."""
        from omnibase_core.errors.exception_compute_pipeline_error import (
            ComputePipelineError,
        )

        error = ComputePipelineError(
            "Transformation failed",
            step_name="normalize_case",
        )

        assert error.step_name == "normalize_case"

    def test_compute_pipeline_error_with_operation(self) -> None:
        """Test ComputePipelineError with operation context."""
        from omnibase_core.errors.exception_compute_pipeline_error import (
            ComputePipelineError,
        )

        error = ComputePipelineError(
            "Operation failed",
            step_name="transform",
            operation="transformation",
        )

        assert error.step_name == "transform"
        assert error.operation == "transformation"

    def test_compute_pipeline_error_with_correlation_id(self) -> None:
        """Test ComputePipelineError preserves correlation_id."""
        from omnibase_core.errors.exception_compute_pipeline_error import (
            ComputePipelineError,
        )

        corr_id = uuid4()
        error = ComputePipelineError(
            "Pipeline error",
            step_name="validate",
            correlation_id=corr_id,
        )

        assert error.correlation_id == corr_id

    def test_compute_pipeline_error_serialization(self) -> None:
        """Test ComputePipelineError can be serialized."""
        from omnibase_core.errors.exception_compute_pipeline_error import (
            ComputePipelineError,
        )

        error = ComputePipelineError(
            "Pipeline error",
            step_name="transform_data",
            operation="mapping",
        )

        # Should have model_dump method from ModelOnexError
        error_dict = error.model_dump()

        assert error_dict["message"] == "Pipeline error"
        assert "correlation_id" in error_dict
        assert "context" in error_dict
        assert error_dict["context"].get("step_name") == "transform_data"
        assert error_dict["context"].get("operation") == "mapping"

    def test_compute_pipeline_error_with_custom_error_code(self) -> None:
        """Test ComputePipelineError with custom error code."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.errors.exception_compute_pipeline_error import (
            ComputePipelineError,
        )

        error = ComputePipelineError(
            "Validation failed",
            step_name="validate_input",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "[ONEX_CORE_006_VALIDATION_ERROR]" in str(error)

    def test_compute_pipeline_error_with_additional_context(self) -> None:
        """Test ComputePipelineError supports additional structured context."""
        from omnibase_core.errors.exception_compute_pipeline_error import (
            ComputePipelineError,
        )

        error = ComputePipelineError(
            "Type mismatch in transformation",
            step_name="case_conversion",
            operation="transformation",
            input_type="int",
            expected_type="str",
        )

        error_dict = error.model_dump()

        # Additional context fields are nested in 'context' dict
        assert "context" in error_dict
        context = error_dict["context"]
        assert context.get("input_type") == "int"
        assert context.get("expected_type") == "str"
        assert context.get("step_name") == "case_conversion"
        assert context.get("operation") == "transformation"


@pytest.mark.timeout(10)
class TestComputePipelineErrorImport:
    """Tests for ComputePipelineError import from errors module."""

    def test_import_from_errors_module(self) -> None:
        """Test ComputePipelineError can be imported from errors module."""
        from omnibase_core.errors import ComputePipelineError

        error = ComputePipelineError(
            "Test error",
            step_name="test_step",
        )

        assert error.step_name == "test_step"
        assert "[ONEX_CORE_165_PROCESSING_ERROR]" in str(error)

    def test_compute_pipeline_error_inherits_model_onex_error(self) -> None:
        """Test ComputePipelineError inherits from ModelOnexError."""
        from omnibase_core.errors import ComputePipelineError
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        error = ComputePipelineError("Test error")

        assert isinstance(error, ModelOnexError)
        assert isinstance(error, Exception)


@pytest.mark.timeout(10)
class TestComputePipelineErrorInvariants:
    """Tests for ComputePipelineError invariants."""

    def test_error_includes_correlation_id(self) -> None:
        """Test ComputePipelineError always includes correlation_id."""
        from omnibase_core.errors.exception_compute_pipeline_error import (
            ComputePipelineError,
        )

        error = ComputePipelineError("test")

        assert hasattr(error, "correlation_id")
        assert error.correlation_id is not None
        assert isinstance(error.correlation_id, UUID)

    def test_no_raw_stack_traces_in_serialization(self) -> None:
        """Test error serialization doesn't include raw stack traces."""
        from omnibase_core.errors.exception_compute_pipeline_error import (
            ComputePipelineError,
        )

        error = ComputePipelineError("test error", step_name="test")
        error_dict = error.model_dump()

        # Should not have __traceback__ or raw stack trace
        assert "__traceback__" not in error_dict
        assert "traceback" not in error_dict

        # Context fields should be structured, not raw exception data
        for _, value in error_dict.items():
            assert not isinstance(value, type(error))  # No nested exceptions

    def test_default_error_code_is_processing_error(self) -> None:
        """Test default error code is PROCESSING_ERROR."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.errors.exception_compute_pipeline_error import (
            ComputePipelineError,
        )

        error = ComputePipelineError("test")

        assert error.error_code == EnumCoreErrorCode.PROCESSING_ERROR
