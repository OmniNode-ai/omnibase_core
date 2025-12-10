"""
Compute Pipeline Error ().

Custom exception for compute pipeline execution errors with structured context.

This exception is raised when a compute pipeline step fails during execution,
providing detailed context about the failure including step name, error type,
and optional correlation tracking.

MVP Classes:
- ComputePipelineError: Base error for all compute pipeline operations

Error Invariants (MVP Requirements):
- All errors MUST include step_name when applicable
- All errors SHOULD include correlation_id for tracking
- Structured fields for logging and observability
- Raw stack traces MUST NOT appear in error envelopes

Design Principles:
- Inherit from ModelOnexError for consistency
- Minimal boilerplate (leverage base class features)
- Type-safe with mypy strict mode compliance
- Serializable for event bus and logging
- No circular dependencies

Usage:
    from omnibase_core.errors.exception_compute_pipeline_error import (
        ComputePipelineError,
    )

    # Pipeline step failure
    raise ComputePipelineError(
        "Transformation failed: unsupported input type",
        step_name="normalize_case",
        operation="transformation",
    )

    # With correlation tracking
    raise ComputePipelineError(
        "Validation step failed",
        step_name="validate_input",
        operation="validation",
        correlation_id=context.correlation_id,
    )
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ComputePipelineError(ModelOnexError):
    """
    Error for compute pipeline execution failures.

    Raised when a compute pipeline step fails during execution. Includes
    step_name for debugging and observability, plus optional operation type.

    Attributes:
        message: Human-readable error message
        error_code: Optional error code (defaults to PROCESSING_ERROR)
        step_name: Name of the pipeline step that failed
        operation: Optional operation type (e.g., "transformation", "mapping", "validation")
        correlation_id: UUID for tracking across system (auto-generated if not provided)
        **context: Additional structured context

    Example:
        raise ComputePipelineError(
            "Case transformation failed: input is not a string",
            step_name="normalize_case",
            operation="transformation",
            input_type=type(input_data).__name__,
        )
    """

    # NOTE: **context: Any is intentional - accepts arbitrary structured context
    # fields for logging, debugging, and observability (e.g., input_type, expected_type, etc.)
    def __init__(
        self,
        message: str,
        step_name: str | None = None,
        error_code: EnumCoreErrorCode | str | None = None,
        status: EnumOnexStatus = EnumOnexStatus.ERROR,
        correlation_id: UUID | None = None,
        timestamp: datetime | None = None,
        operation: str | None = None,
        **context: Any,
    ) -> None:
        """
        Initialize ComputePipelineError with pipeline context.

        Args:
            message: Human-readable error message
            step_name: Name of the pipeline step that failed (optional)
            error_code: Optional error code (defaults to PROCESSING_ERROR if None)
            status: Error status (default: ERROR)
            correlation_id: Optional correlation ID for tracking
            timestamp: Optional timestamp (auto-generated if None)
            operation: Optional operation type (e.g., "transformation", "mapping")
            **context: Additional structured context
        """
        # Use PROCESSING_ERROR as default code if not specified
        final_error_code = error_code or EnumCoreErrorCode.PROCESSING_ERROR

        # Add step_name to context if provided
        if step_name is not None:
            context["step_name"] = step_name

        # Add operation to context if provided
        if operation is not None:
            context["operation"] = operation

        # Call parent with all structured fields
        super().__init__(
            message=message,
            error_code=final_error_code,
            status=status,
            correlation_id=correlation_id,
            timestamp=timestamp,
            **context,
        )

        # Store step_name and operation as attributes for direct access
        self.step_name = step_name
        self.operation = operation


__all__ = [
    "ComputePipelineError",
]
