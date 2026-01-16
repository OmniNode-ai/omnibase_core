"""
Tie Breaker Decision Model for Execution Order Resolution.

This module defines ModelTieBreakerDecision, which records a specific
tie-breaker decision made during resolution.

This is a pure data model with no side effects.

See Also:
    - OMN-1106: Beta Execution Order Resolution Pure Function
    - ModelResolutionMetadata: Contains tie-breaker decisions
    - ModelExecutionOrderingPolicy: Defines the tie-breaker order

.. versionadded:: 0.4.1
    Added as part of Execution Order Resolution (OMN-1106)
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelTieBreakerDecision(BaseModel):
    """
    Records a specific tie-breaker decision made during resolution.

    When two or more handlers have equivalent ordering constraints, a tie-breaker
    is used to determine their relative order. This model records each such
    decision for auditability.

    Attributes:
        phase: The phase where the tie occurred
        handler_ids: The handlers that were tied
        tie_breaker_used: Which tie-breaker resolved the tie
        winning_handler: The handler that was placed first
        reason: Explanation of why this handler won

    Example:
        >>> decision = ModelTieBreakerDecision(
        ...     phase="execute",
        ...     handler_ids=["handler.a", "handler.b"],
        ...     tie_breaker_used="priority",
        ...     winning_handler="handler.a",
        ...     reason="handler.a has priority=1, handler.b has priority=2",
        ... )

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.

    .. versionadded:: 0.4.1
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        validate_assignment=True,
    )

    phase: str = Field(
        ...,
        description="The execution phase where the tie occurred",
    )

    handler_ids: list[str] = Field(
        ...,
        min_length=2,
        description="The handler IDs that were tied (minimum 2)",
    )

    tie_breaker_used: str = Field(
        ...,
        description="Which tie-breaker resolved the tie (e.g., 'priority', 'alphabetical')",
    )

    winning_handler: str = Field(
        ...,
        description="The handler that was placed first after tie-breaking",
    )

    reason: str | None = Field(
        default=None,
        description="Explanation of why this handler won the tie-break",
    )


__all__ = [
    "ModelTieBreakerDecision",
]
