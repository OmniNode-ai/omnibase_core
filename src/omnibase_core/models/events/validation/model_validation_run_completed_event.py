"""
Cross-repo validation run completed event model.

This module provides the event model for when a cross-repo validation run completes.
This event marks the end of a validation lifecycle and contains the summary
of the validation results.

Location:
    ``omnibase_core.models.events.validation.model_validation_run_completed_event``

Import Example:
    .. code-block:: python

        from omnibase_core.models.events.validation import (
            ModelValidationRunCompletedEvent,
            VALIDATION_RUN_COMPLETED_EVENT,
        )

Event Type:
    ``onex.validation.cross_repo.run.completed.v1``

See Also:
    - :class:`ModelValidationRunStartedEvent`: Emitted when validation starts
    - :class:`ModelValidationViolationsBatchEvent`: Emitted for each batch of violations

.. versionadded:: 0.13.0
    Initial implementation as part of OMN-1776 cross-repo orchestrator.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from omnibase_core.models.events.validation.model_validation_event_base import (
    ModelValidationEventBase,
)

__all__ = ["ModelValidationRunCompletedEvent", "VALIDATION_RUN_COMPLETED_EVENT"]

VALIDATION_RUN_COMPLETED_EVENT = "onex.validation.cross_repo.run.completed.v1"


class ModelValidationRunCompletedEvent(ModelValidationEventBase):
    """
    Event emitted when a cross-repo validation run completes.

    This event marks the end of a validation lifecycle. It contains the
    summary of the validation results, enabling dashboards to display
    aggregate metrics without reconstructing from individual violations.

    The model is immutable (frozen) to ensure event integrity after creation.

    Attributes:
        event_type: Event type identifier (onex.validation.cross_repo.run.completed.v1).
        is_valid: Whether the validation passed (no unsuppressed errors).
        total_violations: Total number of violations found.
        error_count: Number of ERROR/CRITICAL/FATAL severity violations.
        warning_count: Number of WARNING severity violations.
        suppressed_count: Number of violations suppressed by baseline.
        files_processed: Number of files scanned.
        rules_applied: Number of rules that were executed.
        duration_ms: Total validation duration in milliseconds.
        completed_at: When the validation run completed (UTC).

    Example:
        >>> from uuid import uuid4
        >>> from datetime import datetime, UTC
        >>> from omnibase_core.models.events.validation import (
        ...     ModelValidationRunCompletedEvent,
        ... )
        >>>
        >>> event = ModelValidationRunCompletedEvent(
        ...     run_id=uuid4(),
        ...     repo_id="omnibase_core",
        ...     is_valid=True,
        ...     total_violations=5,
        ...     error_count=0,
        ...     warning_count=3,
        ...     suppressed_count=2,
        ...     files_processed=150,
        ...     rules_applied=5,
        ...     duration_ms=1250,
        ...     completed_at=datetime.now(UTC),
        ... )
        >>> event.event_type
        'onex.validation.cross_repo.run.completed.v1'

    .. versionadded:: 0.13.0
    """

    event_type: str = Field(
        default=VALIDATION_RUN_COMPLETED_EVENT,
        description="Event type identifier.",
    )

    is_valid: bool = Field(
        ...,
        description="Whether the validation passed (no unsuppressed errors).",
    )

    total_violations: int = Field(
        ...,
        ge=0,
        description="Total number of violations found.",
    )

    error_count: int = Field(
        ...,
        ge=0,
        description="Number of ERROR/CRITICAL/FATAL severity violations.",
    )

    warning_count: int = Field(
        ...,
        ge=0,
        description="Number of WARNING severity violations.",
    )

    suppressed_count: int = Field(
        ...,
        ge=0,
        description="Number of violations suppressed by baseline.",
    )

    files_processed: int = Field(
        ...,
        ge=0,
        description="Number of files scanned.",
    )

    rules_applied: int = Field(
        ...,
        ge=0,
        description="Number of rules that were executed.",
    )

    duration_ms: int = Field(
        ...,
        ge=0,
        description="Total validation duration in milliseconds.",
    )

    completed_at: datetime = Field(
        ...,
        description="When the validation run completed (UTC).",
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate that event_type matches the expected constant."""
        if v != VALIDATION_RUN_COMPLETED_EVENT:
            raise ValueError(
                f"event_type must be '{VALIDATION_RUN_COMPLETED_EVENT}', got '{v}'"
            )
        return v

    @classmethod
    def create(
        cls,
        run_id: UUID,
        repo_id: str,
        is_valid: bool,
        total_violations: int,
        error_count: int,
        warning_count: int,
        suppressed_count: int,
        files_processed: int,
        rules_applied: int,
        duration_ms: int,
        completed_at: datetime,
        *,
        correlation_id: UUID | None = None,
    ) -> "ModelValidationRunCompletedEvent":
        """
        Factory method for creating a validation run completed event.

        Args:
            run_id: Unique identifier for this validation run.
            repo_id: Identifier of the repository being validated.
            is_valid: Whether the validation passed.
            total_violations: Total number of violations found.
            error_count: Number of error-level violations.
            warning_count: Number of warning-level violations.
            suppressed_count: Number of suppressed violations.
            files_processed: Number of files scanned.
            rules_applied: Number of rules executed.
            duration_ms: Validation duration in milliseconds.
            completed_at: When the validation completed.
            correlation_id: Optional correlation ID for tracing.

        Returns:
            A new ModelValidationRunCompletedEvent instance.
        """
        return cls(
            run_id=run_id,
            repo_id=repo_id,
            is_valid=is_valid,
            total_violations=total_violations,
            error_count=error_count,
            warning_count=warning_count,
            suppressed_count=suppressed_count,
            files_processed=files_processed,
            rules_applied=rules_applied,
            duration_ms=duration_ms,
            completed_at=completed_at,
            correlation_id=correlation_id,
        )
