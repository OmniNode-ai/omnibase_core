"""
FilterCondition model.
"""

from pydantic import BaseModel, Field

from .model_filter_operator import ModelFilterOperator


class ModelFilterCondition(BaseModel):
    """Individual filter condition."""

    field: str = Field(default=..., description="Field to filter on")
    operator: ModelFilterOperator = Field(default=..., description="Filter operator")
    negate: bool = Field(default=False, description="Negate the condition")


# Compatibility alias
FilterCondition = ModelFilterCondition
