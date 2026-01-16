"""
ModelCorpusStatistics - Statistics model for execution corpus.

This module provides the ModelCorpusStatistics model which contains
computed statistics for an execution corpus, including handler distribution,
success rates, and timing characteristics.

Thread Safety:
    ModelCorpusStatistics is frozen (immutable) after creation, making it
    safe to share across threads.

Usage:
    .. code-block:: python

        from omnibase_core.models.replay import ModelCorpusStatistics

        stats = ModelCorpusStatistics(
            total_executions=100,
            success_count=85,
            failure_count=15,
            handler_distribution={"text-transform": 50, "json-parse": 50},
            success_rate=0.85,
            avg_duration_ms=150.5,
        )
        print(f"Success rate: {stats.success_rate:.1%}")

Related:
    - OMN-1202: Execution Corpus Model for beta demo
    - ModelExecutionCorpus: Collection of execution manifests

.. versionadded:: 0.4.0
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError


class ModelCorpusStatistics(BaseModel):
    """
    Computed statistics for an execution corpus.

    Statistics are calculated from the collection of execution manifests
    in a corpus, providing insights into handler distribution, success
    rates, and timing characteristics.

    Attributes:
        total_executions: Total number of executions in the corpus.
        success_count: Number of successful executions.
        failure_count: Number of failed executions.
        handler_distribution: Count of executions by handler/node ID.
        success_rate: Fraction of successful executions (0.0 to 1.0).
        avg_duration_ms: Average execution duration in milliseconds.

    Thread Safety:
        This model is frozen (immutable) after creation, making it safe
        to share across threads.

    Example:
        >>> stats = ModelCorpusStatistics(
        ...     total_executions=100,
        ...     success_count=85,
        ...     failure_count=15,
        ...     handler_distribution={"text-transform": 50, "json-parse": 50},
        ...     success_rate=0.85,
        ...     avg_duration_ms=150.5,
        ... )
        >>> stats.success_rate
        0.85

    .. versionadded:: 0.4.0
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    total_executions: int = Field(
        default=0,
        ge=0,
        description="Total number of executions in the corpus",
    )

    success_count: int = Field(
        default=0,
        ge=0,
        description="Number of successful executions",
    )

    failure_count: int = Field(
        default=0,
        ge=0,
        description="Number of failed executions",
    )

    handler_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Count of executions by handler/node ID",
    )

    success_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of successful executions (0.0 to 1.0)",
    )

    avg_duration_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="Average execution duration in milliseconds",
    )

    @model_validator(mode="after")
    def _validate_counts(self) -> "ModelCorpusStatistics":
        """Validate that success_count + failure_count == total_executions.

        Returns:
            Self if validation passes.

        Raises:
            ModelOnexError: If counts don't add up to total.
        """
        if self.success_count + self.failure_count != self.total_executions:
            msg = (
                f"success_count ({self.success_count}) + failure_count ({self.failure_count}) "
                f"must equal total_executions ({self.total_executions})"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return self

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return (
            f"CorpusStats({self.total_executions} executions, "
            f"{self.success_rate:.1%} success, "
            f"{self.success_count} passed, {self.failure_count} failed)"
        )

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelCorpusStatistics(total_executions={self.total_executions}, "
            f"success_count={self.success_count}, "
            f"failure_count={self.failure_count}, "
            f"success_rate={self.success_rate}, "
            f"handler_count={len(self.handler_distribution)}, "
            f"avg_duration_ms={self.avg_duration_ms})"
        )


__all__ = ["ModelCorpusStatistics"]
