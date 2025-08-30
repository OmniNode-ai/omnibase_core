"""
Model for optimization result.

Result of quota optimization run.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from omnibase_core.model.optimization.model_optimization_metadata import \
    ModelOptimizationMetadata
from omnibase_core.model.optimization.model_reallocation import \
    ModelReallocation


class ModelOptimizationResult(BaseModel):
    """Result of quota optimization run."""

    optimization_id: str = Field(..., description="Unique optimization ID")
    timestamp: datetime = Field(..., description="When optimization ran")

    success: bool = Field(..., description="Whether optimization succeeded")

    reallocations: List[ModelReallocation] = Field(
        default_factory=list, description="Quota reallocations performed"
    )

    efficiency_before: float = Field(
        ..., ge=0, le=1, description="Efficiency before optimization"
    )
    efficiency_after: float = Field(
        ..., ge=0, le=1, description="Efficiency after optimization"
    )

    tokens_saved: int = Field(0, ge=0, description="Tokens saved through optimization")
    cost_saved: float = Field(0.0, ge=0, description="Cost saved in USD")

    recommendations: List[str] = Field(
        default_factory=list, description="Additional recommendations"
    )

    metadata: Optional[ModelOptimizationMetadata] = Field(
        default_factory=ModelOptimizationMetadata,
        description="Additional optimization data",
    )

    def get_improvement(self) -> float:
        """Get efficiency improvement percentage."""
        if self.efficiency_before == 0:
            return 0.0
        return (
            (self.efficiency_after - self.efficiency_before) / self.efficiency_before
        ) * 100
