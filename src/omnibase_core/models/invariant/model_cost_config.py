"""Configuration for cost invariant.

Enforces budget constraints on operations, useful for
LLM API calls and other metered resources.
"""

from pydantic import BaseModel, Field


class ModelCostConfig(BaseModel):
    """Configuration for cost invariant.

    Enforces budget constraints on operations, useful for
    LLM API calls and other metered resources.
    """

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
