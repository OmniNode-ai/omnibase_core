"""
ModelCorpusReplayResult - Aggregate result from corpus replay.

This module provides the ModelCorpusReplayResult model for capturing
the complete result of replaying an execution corpus, including
individual results, aggregate metrics, and timing information.

Thread Safety:
    ModelCorpusReplayResult is frozen (immutable) after creation, making it
    safe to share across threads.

Usage:
    .. code-block:: python

        from omnibase_core.models.replay import ModelCorpusReplayResult
        from uuid import uuid4

        result = ModelCorpusReplayResult(
            corpus_id=uuid4(),
            corpus_name="production-sample",
            total_executions=50,
            successful=45,
            failed=3,
            skipped=2,
            execution_results=results,
            aggregate_metrics=metrics,
            duration_ms=5000.0,
        )
        print(f"Success rate: {result.success_rate:.1%}")

Related:
    - OMN-1204: Corpus Replay Orchestrator
    - ServiceCorpusReplayOrchestrator: Service that produces this result

.. versionadded:: 0.6.0
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.replay.model_aggregate_metrics import ModelAggregateMetrics
from omnibase_core.models.replay.model_single_replay_result import (
    ModelSingleReplayResult,
)


class ModelCorpusReplayResult(BaseModel):
    """
    Aggregate result from replaying an execution corpus.

    Contains complete results from a corpus replay including individual
    execution results, aggregate metrics, configuration used, and timing.

    Attributes:
        corpus_id: ID of the corpus that was replayed.
        corpus_name: Name of the corpus that was replayed.
        total_executions: Total number of executions attempted.
        successful: Number of successful replays.
        failed: Number of failed replays.
        skipped: Number of skipped replays (filtered or cancelled).
        execution_results: Individual results for each execution.
        aggregate_metrics: Computed aggregate metrics.
        config_overrides: Configuration overrides that were applied.
        duration_ms: Total wall-clock duration in milliseconds.
        started_at: When the replay started.
        completed_at: When the replay completed.
        was_cancelled: Whether the replay was cancelled.
        fail_fast_triggered: Whether fail-fast mode stopped the replay.

    Thread Safety:
        This model is frozen (immutable) after creation, making it safe
        to share across threads.

    Example:
        >>> result = ModelCorpusReplayResult(
        ...     corpus_id=uuid4(),
        ...     corpus_name="test",
        ...     total_executions=50,
        ...     successful=45,
        ...     failed=5,
        ...     skipped=0,
        ...     execution_results=[],
        ...     aggregate_metrics=ModelAggregateMetrics(),
        ...     duration_ms=5000.0,
        ... )
        >>> result.success_rate
        0.9

    .. versionadded:: 0.6.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    corpus_id: UUID = Field(
        ...,
        description="ID of the corpus that was replayed",
    )

    corpus_name: str = Field(
        ...,
        description="Name of the corpus that was replayed",
    )

    total_executions: int = Field(
        ...,
        ge=0,
        description="Total number of executions attempted",
    )

    successful: int = Field(
        default=0,
        ge=0,
        description="Number of successful replays",
    )

    failed: int = Field(
        default=0,
        ge=0,
        description="Number of failed replays",
    )

    skipped: int = Field(
        default=0,
        ge=0,
        description="Number of skipped replays (filtered or cancelled)",
    )

    execution_results: tuple[ModelSingleReplayResult, ...] = Field(
        default_factory=tuple,
        description="Individual results for each execution",
    )

    aggregate_metrics: ModelAggregateMetrics = Field(
        default_factory=ModelAggregateMetrics,
        description="Computed aggregate metrics",
    )

    # ONEX_EXCLUDE: dict_str_any - user-provided config overrides with arbitrary structure
    config_overrides: dict[str, Any] | None = Field(
        default=None,
        description="Configuration overrides that were applied",
    )

    duration_ms: float = Field(
        ...,
        ge=0.0,
        description="Total wall-clock duration in milliseconds",
    )

    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the replay started",
    )

    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the replay completed",
    )

    was_cancelled: bool = Field(
        default=False,
        description="Whether the replay was cancelled",
    )

    fail_fast_triggered: bool = Field(
        default=False,
        description="Whether fail-fast mode stopped the replay early",
    )

    @model_validator(mode="after")
    def _validate_counts(self) -> ModelCorpusReplayResult:
        """Validate that counts add up correctly.

        Returns:
            Self if validation passes.

        Raises:
            ModelOnexError: If counts don't add up.
        """
        total_processed = self.successful + self.failed + self.skipped
        if total_processed > self.total_executions:
            msg = (
                f"successful ({self.successful}) + failed ({self.failed}) + "
                f"skipped ({self.skipped}) = {total_processed} exceeds "
                f"total_executions ({self.total_executions})"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return self

    @property
    def success_rate(self) -> float:
        """Calculate success rate.

        Returns:
            Fraction of successful replays (0.0 to 1.0).
        """
        total_attempted = self.successful + self.failed
        if total_attempted == 0:
            return 1.0  # No failures if nothing was attempted
        return self.successful / total_attempted

    @property
    def is_complete(self) -> bool:
        """Check if all executions were processed.

        Returns:
            True if no remaining unprocessed executions.
        """
        return self.successful + self.failed + self.skipped == self.total_executions

    @property
    def all_successful(self) -> bool:
        """Check if all replays were successful.

        Returns:
            True if failed == 0 and not cancelled.
        """
        return self.failed == 0 and not self.was_cancelled

    def get_failed_results(self) -> tuple[ModelSingleReplayResult, ...]:
        """Get all failed execution results.

        Returns:
            Tuple of results where success is False.
        """
        return tuple(r for r in self.execution_results if not r.success)

    def get_successful_results(self) -> tuple[ModelSingleReplayResult, ...]:
        """Get all successful execution results.

        Returns:
            Tuple of results where success is True.
        """
        return tuple(r for r in self.execution_results if r.success)

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        status = "PASS" if self.all_successful else "FAIL"
        return (
            f"CorpusReplayResult({self.corpus_name}, {status}, "
            f"{self.successful}/{self.total_executions} ok, "
            f"{self.duration_ms:.1f}ms)"
        )


__all__ = ["ModelCorpusReplayResult"]
