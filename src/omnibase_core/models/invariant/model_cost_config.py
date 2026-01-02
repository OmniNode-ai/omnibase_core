"""Configuration for cost invariant.

Enforces budget constraints on operations, useful for
LLM API calls and other metered resources.

Thread Safety:
    ModelCostConfig is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelCostConfig(BaseModel):
    """Configuration for cost invariant.

    Enforces budget constraints on operations, useful for LLM API calls
    and other metered resources. Allows specifying maximum cost per unit
    of operation.

    Attributes:
        max_cost: Maximum cost allowed per unit. Must be greater than zero.
        per: Cost unit for measurement. Common values are 'request' (per API
            call), 'token' (per input/output token), or custom units.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access. No synchronization is needed
        when sharing instances across threads.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    max_cost: float = Field(
        ...,
        gt=0,
        description="Maximum cost allowed per unit",
    )
    per: str = Field(
        default="request",
        description="Cost unit: 'request', 'token', or custom unit",
    )


__all__ = ["ModelCostConfig"]
