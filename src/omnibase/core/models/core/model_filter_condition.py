"""
FilterCondition model.
"""

from pydantic import BaseModel, Field

from .model_filter_operator import ModelFilterOperator


class ModelFilterCondition(BaseModel):
    """Individual filter condition."""

    field: str = Field(..., description="Field to filter on")
    operator: ModelFilterOperator = Field(..., description="Filter operator")
    negate: bool = Field(False, description="Negate the condition")


# Backward compatibility alias
FilterCondition = ModelFilterCondition
