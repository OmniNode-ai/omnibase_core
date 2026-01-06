# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
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

from pydantic import BaseModel, ConfigDict, Field


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

    See Also:
        - :class:`~omnibase_core.models.omnimemory.model_cost_ledger.ModelCostLedger`:
          The parent ledger containing cost entries

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
        """Return a human-readable string representation."""
        return (
            f"CostEntry({self.operation}@{self.model_used}: "
            f"${self.cost:.4f}, tokens={self.total_tokens})"
        )

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelCostEntry(entry_id={self.entry_id!r}, "
            f"operation={self.operation!r}, "
            f"model_used={self.model_used!r}, "
            f"cost={self.cost!r}, "
            f"cumulative_total={self.cumulative_total!r})"
        )


# Export for use
__all__ = ["ModelCostEntry"]
