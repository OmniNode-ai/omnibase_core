"""
Model for optimization opportunity.

Identified optimization opportunity for cost savings.
"""

from pydantic import BaseModel, Field


class ModelOptimizationOpportunity(BaseModel):
    """Identified optimization opportunity."""

    opportunity_id: str = Field(..., description="Unique opportunity ID")
    category: str = Field(..., description="Opportunity category")
    description: str = Field(..., description="Opportunity description")
    potential_savings: float = Field(..., description="Potential cost savings")
    implementation_effort: str = Field(..., description="Implementation effort level")
    priority: str = Field(..., description="Priority level")
