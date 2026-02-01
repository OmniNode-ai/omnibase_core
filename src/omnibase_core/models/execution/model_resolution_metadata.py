"""
Resolution Metadata Model for Execution Order Resolution.

This module defines ModelResolutionMetadata, which captures metadata about
the resolution process including the strategy used, tie-breaker decisions,
and timing information.

This is a pure data model with no side effects.

See Also:
    - OMN-1106: Beta Execution Order Resolution Pure Function
    - ModelExecutionOrderingPolicy: The policy that drives resolution
    - ModelExecutionPlan: The plan that includes this metadata

.. versionadded:: 0.4.1
    Added as part of Execution Order Resolution (OMN-1106)
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.execution.model_tie_breaker_decision import (
    ModelTieBreakerDecision,
)


class ModelResolutionMetadata(BaseModel):
    """
    Metadata about the execution order resolution process.

    This model captures comprehensive information about how the execution
    plan was resolved, including the strategy used, any tie-breaker decisions
    made, timing information, and statistics about the resolution.

    The model is immutable (frozen) to ensure thread safety and prevent
    modification after resolution completes.

    Attributes:
        strategy: The ordering strategy used (e.g., "topological_sort")
        tie_breaker_order: Ordered list of tie-breakers applied
        tie_breaker_decisions: Specific tie-breaker decisions made
        deterministic: Whether the ordering is deterministic
        resolution_started_at: When resolution started
        resolution_completed_at: When resolution completed
        resolution_duration_ms: Duration in milliseconds
        total_handlers_resolved: Total number of handlers placed in the plan
        total_constraints_evaluated: Total constraints checked
        source_profile: Reference to the execution profile used
        resolver_ver: Version of the resolver that produced this plan

    Example:
        >>> from datetime import datetime
        >>> metadata = ModelResolutionMetadata(
        ...     strategy="topological_sort",
        ...     tie_breaker_order=["priority", "alphabetical"],
        ...     deterministic=True,
        ...     resolution_started_at=datetime.now(),
        ...     total_handlers_resolved=5,
        ...     total_constraints_evaluated=12,
        ... )
        >>> metadata.strategy
        'topological_sort'

    See Also:
        - ModelExecutionOrderingPolicy: Defines the ordering strategy
        - ModelExecutionPlan: Contains this metadata

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.

    .. versionadded:: 0.4.1
        Added as part of Execution Order Resolution (OMN-1106)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        validate_assignment=True,
    )

    # Strategy used
    strategy: Literal["topological_sort"] = Field(
        default="topological_sort",
        description="The ordering strategy used for resolution",
    )

    # Tie-breaker configuration
    tie_breaker_order: list[Literal["priority", "alphabetical"]] = Field(
        default=["priority", "alphabetical"],
        description="Ordered list of tie-breakers applied when handlers are equivalent",
    )

    tie_breaker_decisions: list[ModelTieBreakerDecision] = Field(
        default_factory=list,
        description="Specific tie-breaker decisions made during resolution",
    )

    deterministic: bool = Field(
        default=True,
        description="Whether the ordering is deterministic across runs",
    )

    # Timing information
    resolution_started_at: datetime | None = Field(
        default=None,
        description="Timestamp when resolution started",
    )

    resolution_completed_at: datetime | None = Field(
        default=None,
        description="Timestamp when resolution completed",
    )

    resolution_duration_ms: float | None = Field(
        default=None,
        ge=0,
        description="Duration of resolution in milliseconds",
    )

    # Statistics
    total_handlers_resolved: int = Field(
        default=0,
        ge=0,
        description="Total number of handlers placed in the execution plan",
    )

    total_constraints_evaluated: int = Field(
        default=0,
        ge=0,
        description="Total number of constraints checked during resolution",
    )

    phases_with_handlers: int = Field(
        default=0,
        ge=0,
        description="Number of phases that have at least one handler",
    )

    tie_breaker_statistics: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Count of how often each tie-breaker was applied "
            "(e.g., {'priority': 5, 'alphabetical': 12})"
        ),
    )

    # Source information
    source_profile: str | None = Field(
        default=None,
        description="Reference to the execution profile that defined phases/policy",
    )

    resolver_ver: str | None = Field(
        default=None,
        description="Version of the resolver that produced this plan",
    )

    def tie_breaker_count(self) -> int:
        """
        Get the number of tie-breaker decisions made.

        Returns:
            Count of tie-breaker decisions.
        """
        return len(self.tie_breaker_decisions)

    def had_ties(self) -> bool:
        """
        Check if any tie-breaking was needed.

        Returns:
            True if at least one tie-breaker decision was made.
        """
        return len(self.tie_breaker_decisions) > 0

    def get_resolution_duration(self) -> float | None:
        """
        Get resolution duration, computing from timestamps if needed.

        Returns:
            Duration in milliseconds, or None if timing not available.
        """
        if self.resolution_duration_ms is not None:
            return self.resolution_duration_ms
        if self.resolution_started_at and self.resolution_completed_at:
            delta = self.resolution_completed_at - self.resolution_started_at
            return delta.total_seconds() * 1000
        return None

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        ties = f", {self.tie_breaker_count()} ties" if self.had_ties() else ""
        duration = (
            f", {self.resolution_duration_ms:.2f}ms"
            if self.resolution_duration_ms
            else ""
        )
        return (
            f"ResolutionMetadata({self.strategy}, "
            f"{self.total_handlers_resolved} handlers{ties}{duration})"
        )

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelResolutionMetadata(strategy={self.strategy!r}, "
            f"total_handlers_resolved={self.total_handlers_resolved}, "
            f"total_constraints_evaluated={self.total_constraints_evaluated}, "
            f"tie_breaker_decisions={len(self.tie_breaker_decisions)}, "
            f"deterministic={self.deterministic})"
        )


__all__ = [
    "ModelResolutionMetadata",
]
