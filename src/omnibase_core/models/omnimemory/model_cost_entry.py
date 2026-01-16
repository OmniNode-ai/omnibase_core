"""
ModelCostEntry - Individual cost entry for cost ledger tracking.

Defines the ModelCostEntry model which represents a single billable LLM
operation with its cost impact. Each entry tracks token counts, model used,
and maintains a running cumulative total for budget tracking.

This is a pure data model with no side effects.

.. versionadded:: 0.6.0
    Added as part of OmniMemory cost tracking infrastructure (OMN-1239)
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.utils.util_validators import ensure_timezone_aware


class ModelCostEntry(BaseModel):
    """Single cost entry in the ledger.

    Tracks a single billable operation with its cost impact, including
    token counts, model used, and running cumulative total.

    Attributes:
        entry_id: Unique identifier for this entry (auto-generated).
        timestamp: When the operation occurred.
        operation: Description of the operation (e.g., "chat_completion").
        model_used: The LLM model name (e.g., "gpt-4", "claude-3-opus").
        tokens_in: Number of input tokens consumed.
        tokens_out: Number of output tokens generated.
        cost: Cost of this individual operation in USD.
        cumulative_total: Running total cost at time of entry.

    Note:
        Cost values use Python floats for convenience. For applications requiring
        exact decimal precision (e.g., financial auditing), consider converting
        to Decimal at the application layer.

    Example:
        >>> from datetime import datetime, UTC
        >>> entry = ModelCostEntry(
        ...     timestamp=datetime.now(UTC),
        ...     operation="chat_completion",
        ...     model_used="gpt-4",
        ...     tokens_in=150,
        ...     tokens_out=50,
        ...     cost=0.0065,
        ...     cumulative_total=0.0065,
        ... )
        >>> entry.total_tokens
        200

    .. versionadded:: 0.6.0
        Added as part of OmniMemory cost tracking infrastructure (OMN-1239)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # === Required Fields ===

    entry_id: UUID = Field(
        default_factory=uuid4,
        description="Unique entry identifier",
    )

    timestamp: datetime = Field(
        ...,
        description="When the operation occurred",
    )

    operation: str = Field(
        ...,
        min_length=1,
        description="Description of the billable operation",
    )

    model_used: str = Field(
        ...,
        min_length=1,
        description="LLM model name used for the operation",
    )

    tokens_in: int = Field(
        ...,
        ge=0,
        description="Number of input tokens",
    )

    tokens_out: int = Field(
        ...,
        ge=0,
        description="Number of output tokens",
    )

    cost: float = Field(
        ...,
        ge=0.0,
        description="Cost of this operation in USD",
    )

    cumulative_total: float = Field(
        ...,
        ge=0.0,
        description="Running total at time of entry",
    )

    # === Validators ===

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_has_timezone(cls, v: datetime) -> datetime:
        """Validate timestamp is timezone-aware using shared utility."""
        return ensure_timezone_aware(v, "timestamp")

    @model_validator(mode="after")
    def validate_cumulative_total_ge_cost(self) -> "ModelCostEntry":
        """Ensure cumulative_total is at least as large as cost.

        The cumulative total represents the running sum of all costs,
        so it must be greater than or equal to any individual cost entry.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If cumulative_total is less than cost.
        """
        if self.cumulative_total < self.cost:
            raise ValueError(
                f"cumulative_total ({self.cumulative_total}) must be >= cost ({self.cost}). "
                "The cumulative total represents the running sum of all costs."
            )
        return self

    # === Utility Properties ===

    @property
    def total_tokens(self) -> int:
        """
        Get the total number of tokens (input + output).

        Returns:
            Total token count for this operation
        """
        return self.tokens_in + self.tokens_out

    # === Utility Methods ===

    def __str__(self) -> str:
        return (
            f"CostEntry({self.operation}@{self.model_used}: "
            f"${self.cost:.4f}, tokens={self.total_tokens})"
        )

    def __repr__(self) -> str:
        return (
            f"ModelCostEntry(entry_id={self.entry_id!r}, "
            f"operation={self.operation!r}, "
            f"model_used={self.model_used!r}, "
            f"cost={self.cost!r}, "
            f"cumulative_total={self.cumulative_total!r})"
        )


# Export for use
__all__ = ["ModelCostEntry"]
