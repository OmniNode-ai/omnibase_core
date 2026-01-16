"""
ModelSingleReplayResult - Result from single execution replay.

This module provides the ModelSingleReplayResult model for capturing
the result of replaying a single execution manifest, including
success/failure status, timing, and any errors encountered.

Thread Safety:
    ModelSingleReplayResult is frozen (immutable) after creation, making it
    safe to share across threads.

Usage:
    .. code-block:: python

        from omnibase_core.models.replay import ModelSingleReplayResult
        from uuid import uuid4

        # Successful replay
        result = ModelSingleReplayResult(
            manifest_id=uuid4(),
            success=True,
            duration_ms=150.5,
        )

        # Failed replay
        result = ModelSingleReplayResult(
            manifest_id=uuid4(),
            success=False,
            duration_ms=50.0,
            error_message="Timeout exceeded",
            error_type="TimeoutError",
        )

Related:
    - OMN-1204: Corpus Replay Orchestrator
    - ModelCorpusReplayResult: Aggregate result containing these

.. versionadded:: 0.6.0
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelSingleReplayResult(BaseModel):
    """
    Result from replaying a single execution manifest.

    Captures success/failure status, timing information, and any
    errors encountered during replay. Also stores the original and
    replayed outputs for comparison.

    Attributes:
        manifest_id: ID of the execution manifest that was replayed.
        success: Whether the replay completed successfully.
        duration_ms: Replay execution duration in milliseconds.
        error_message: Error message if replay failed.
        error_type: Type name of the error if replay failed.
        error_context: Additional error context (e.g., stack trace).
        original_output: Output from original execution (for comparison).
        replayed_output: Output from replay execution (for comparison).
        outputs_match: Whether original and replayed outputs match.
        retry_count: Number of retries before success/failure.
        completed_at: Timestamp when replay completed.

    Thread Safety:
        This model is frozen (immutable) after creation, making it safe
        to share across threads.

    Example:
        >>> result = ModelSingleReplayResult(
        ...     manifest_id=uuid4(),
        ...     success=True,
        ...     duration_ms=150.5,
        ... )
        >>> result.is_success
        True

    .. versionadded:: 0.6.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    manifest_id: UUID = Field(
        ...,
        description="ID of the execution manifest that was replayed",
    )

    success: bool = Field(
        ...,
        description="Whether the replay completed successfully",
    )

    duration_ms: float = Field(
        ...,
        ge=0.0,
        description="Replay execution duration in milliseconds",
    )

    error_message: str | None = Field(
        default=None,
        description="Error message if replay failed",
    )

    error_type: str | None = Field(
        default=None,
        description="Type name of the error if replay failed",
    )

    # ONEX_EXCLUDE: dict_str_any - arbitrary exception metadata (stack trace, etc.)
    error_context: dict[str, Any] | None = Field(
        default=None,
        description="Additional error context (e.g., stack trace)",
    )

    original_output: Any | None = Field(
        default=None,
        description="Output from original execution (for comparison)",
    )

    replayed_output: Any | None = Field(
        default=None,
        description="Output from replay execution (for comparison)",
    )

    outputs_match: bool | None = Field(
        default=None,
        description="Whether original and replayed outputs match",
    )

    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of retries before success/failure",
    )

    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when replay completed",
    )

    @property
    def is_success(self) -> bool:
        """Check if replay was successful.

        Returns:
            True if success is True.
        """
        return self.success

    @property
    def is_failure(self) -> bool:
        """Check if replay failed.

        Returns:
            True if success is False.
        """
        return not self.success

    @property
    def has_output_mismatch(self) -> bool:
        """Check if outputs don't match.

        Returns:
            True if outputs_match is explicitly False.
        """
        return self.outputs_match is False

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        status = "OK" if self.success else f"FAIL: {self.error_type}"
        return f"ReplayResult({self.manifest_id}, {status}, {self.duration_ms:.1f}ms)"


__all__ = ["ModelSingleReplayResult"]
