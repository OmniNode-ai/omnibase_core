"""
ModelFailureRecord - Failure recorded as state for learning and analysis.

Defines the ModelFailureRecord model which represents a failure event
captured for learning and systematic analysis. Failures become learnable
assets that inform retry strategies, alerting, and post-mortem analysis.

This is a pure data model with no side effects.

.. versionadded:: 0.6.0
    Added as part of OmniMemory failure tracking infrastructure (OMN-1242)
"""

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_failure_type import EnumFailureType
from omnibase_core.utils.util_validators import ensure_timezone_aware


class ModelFailureRecord(BaseModel):
    """Failure recorded as state for learning and analysis.

    Tracks a single failure event with its classification, context, and
    recovery information. Each record captures sufficient detail to enable
    systematic analysis of failure patterns across agent executions.

    Attributes:
        failure_id: Unique identifier for this failure (auto-generated).
        timestamp: When the failure occurred (must be timezone-aware).
        failure_type: Classification of the failure type.
        step_context: Context of the step that failed.
        error_code: Error code for categorization.
        error_message: Human-readable error message.
        model_used: LLM model in use when failure occurred (optional).
        retry_attempt: Which retry attempt this was (0 = first attempt).
        recovery_action: Action taken to recover (optional).
        recovery_outcome: Result of recovery attempt (optional).
        should_remember: Mark failures worth learning from.

    Example:
        >>> from datetime import datetime, UTC
        >>> from omnibase_core.enums.enum_failure_type import EnumFailureType
        >>> record = ModelFailureRecord(
        ...     timestamp=datetime.now(UTC),
        ...     failure_type=EnumFailureType.TIMEOUT,
        ...     step_context="code_generation",
        ...     error_code="TIMEOUT_001",
        ...     error_message="Operation exceeded 30s timeout",
        ...     model_used="gpt-4",
        ...     retry_attempt=0,
        ... )
        >>> record.failure_type.is_retryable()
        True

    .. versionadded:: 0.6.0
        Added as part of OmniMemory failure tracking infrastructure (OMN-1242)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # === Identity ===

    failure_id: UUID = Field(
        default_factory=uuid4,
        description="Unique failure identifier",
    )

    timestamp: datetime = Field(
        ...,
        description="When the failure occurred",
    )

    # === What Failed ===

    failure_type: EnumFailureType = Field(
        ...,
        description="Classification of the failure",
    )

    step_context: str = Field(
        ...,
        min_length=1,
        description="Context of the step that failed",
    )

    error_code: str = Field(
        ...,
        min_length=1,
        description="Error code for categorization",
    )

    error_message: str = Field(
        ...,
        min_length=1,
        description="Human-readable error message",
    )

    # === Conditions ===

    model_used: str | None = Field(
        default=None,
        description="LLM model in use when failure occurred",
    )

    retry_attempt: int = Field(
        default=0,
        ge=0,
        description="Which retry attempt this was",
    )

    # === Recovery ===

    recovery_action: str | None = Field(
        default=None,
        description="Action taken to recover",
    )

    recovery_outcome: Literal["success", "failure", "pending"] | None = Field(
        default=None,
        description="Result of recovery attempt",
    )

    # === Learning Signal ===

    should_remember: bool = Field(
        default=True,
        description="Mark failures worth learning from",
    )

    # === Validators ===

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_has_timezone(cls, v: datetime) -> datetime:
        """Validate timestamp is timezone-aware using shared utility."""
        return ensure_timezone_aware(v, "timestamp")

    # === Utility Methods ===

    def __str__(self) -> str:
        return (
            f"FailureRecord({self.failure_type.value}@{self.step_context}: "
            f"{self.error_code}, retry={self.retry_attempt})"
        )

    def __repr__(self) -> str:
        return (
            f"ModelFailureRecord(failure_id={self.failure_id!r}, "
            f"failure_type={self.failure_type!r}, "
            f"step_context={self.step_context!r}, "
            f"error_code={self.error_code!r}, "
            f"retry_attempt={self.retry_attempt!r})"
        )


# Export for use
__all__ = ["ModelFailureRecord"]
