"""
ModelCorpusReplayProgress - Progress tracking for corpus replay.

This module provides the ModelCorpusReplayProgress model for tracking
progress during corpus replay execution, including counts, timing,
and current execution information.

Thread Safety:
    ModelCorpusReplayProgress is frozen (immutable) after creation.
    New progress instances are created for each update.

Usage:
    .. code-block:: python

        from omnibase_core.models.replay import ModelCorpusReplayProgress

        progress = ModelCorpusReplayProgress(
            total=50,
            completed=25,
            failed=2,
            skipped=0,
            current_manifest="manifest-123",
        )
        print(f"Progress: {progress.completion_percent:.1f}%")

Related:
    - OMN-1204: Corpus Replay Orchestrator
    - ServiceCorpusReplayOrchestrator: Service that emits progress

.. versionadded:: 0.6.0
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError


class ModelCorpusReplayProgress(BaseModel):
    """
    Progress tracking for corpus replay execution.

    Provides real-time progress information during corpus replay,
    including counts, timing estimates, and current execution details.

    Attributes:
        total: Total number of executions to replay.
        completed: Number of successfully completed executions.
        failed: Number of failed executions.
        skipped: Number of skipped executions (filtered out or cancelled).
        current_manifest: String representation of the currently executing manifest ID.
        current_execution_index: Index of current execution (0-based).
        elapsed_ms: Total elapsed time in milliseconds.
        estimated_remaining_ms: Estimated time remaining in milliseconds.

    Thread Safety:
        This model is frozen (immutable) after creation. The orchestrator
        creates new progress instances for each update.

    Example:
        >>> progress = ModelCorpusReplayProgress(
        ...     total=50,
        ...     completed=25,
        ...     failed=2,
        ...     skipped=0,
        ... )
        >>> progress.remaining
        23
        >>> progress.completion_percent
        54.0

    .. versionadded:: 0.6.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    total: int = Field(
        ...,
        ge=0,
        description="Total number of executions to replay",
    )

    completed: int = Field(
        default=0,
        ge=0,
        description="Number of successfully completed executions",
    )

    failed: int = Field(
        default=0,
        ge=0,
        description="Number of failed executions",
    )

    skipped: int = Field(
        default=0,
        ge=0,
        description="Number of skipped executions (filtered out or cancelled)",
    )

    current_manifest: str | None = Field(
        default=None,
        description="String representation of the currently executing manifest ID",
    )

    current_execution_index: int | None = Field(
        default=None,
        ge=0,
        description="Index of current execution (0-based)",
    )

    elapsed_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total elapsed time in milliseconds",
    )

    estimated_remaining_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="Estimated time remaining in milliseconds",
    )

    @model_validator(mode="after")
    def _validate_counts(self) -> "ModelCorpusReplayProgress":
        """Validate that counts don't exceed total.

        This ensures the `remaining` property never returns a negative value.

        Returns:
            Self if validation passes.

        Raises:
            ModelOnexError: If sum of counts exceeds total.
        """
        count_sum = self.completed + self.failed + self.skipped
        if count_sum > self.total:
            raise ModelOnexError(
                message=f"Sum of counts ({count_sum}) exceeds total ({self.total})",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return self

    @property
    def remaining(self) -> int:
        """Get number of remaining executions.

        Returns:
            Number of executions not yet processed (always >= 0).

        Note:
            The model_validator ensures counts don't exceed total,
            guaranteeing this property never returns a negative value.
        """
        result = self.total - self.completed - self.failed - self.skipped
        # Belt-and-suspenders: model_validator already ensures this,
        # but assert for defensive programming in case of future changes
        assert result >= 0, f"remaining cannot be negative: {result}"
        return result

    @property
    def processed(self) -> int:
        """Get number of processed executions.

        Returns:
            Total of completed + failed + skipped.
        """
        return self.completed + self.failed + self.skipped

    @property
    def completion_percent(self) -> float:
        """Get completion percentage.

        Returns:
            Percentage of executions processed (0.0 to 100.0).
        """
        if self.total == 0:
            return 100.0
        return (self.processed / self.total) * 100.0

    @property
    def is_complete(self) -> bool:
        """Check if all executions have been processed.

        Returns:
            True if no remaining executions.
        """
        return self.remaining == 0

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return (
            f"Progress({self.processed}/{self.total}, "
            f"{self.completion_percent:.1f}%, "
            f"ok={self.completed}, fail={self.failed}, skip={self.skipped})"
        )


__all__ = ["ModelCorpusReplayProgress"]
