"""
Model for usage prediction.

Usage prediction for optimization.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.model.optimization.model_prediction_factors import (
    ModelPredictionFactors,
)
from omnibase_core.model.optimization.model_prediction_metadata import (
    ModelPredictionMetadata,
)


class ModelUsagePrediction(BaseModel):
    """Usage prediction for optimization."""

    prediction_id: str = Field(..., description="Unique prediction ID")
    window_id: str = Field(..., description="Window being predicted")
    prediction_time: datetime = Field(..., description="When prediction was made")
    target_time: datetime = Field(..., description="Time being predicted for")

    predicted_tokens: int = Field(..., ge=0, description="Predicted token usage")
    confidence_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Prediction confidence",
    )

    lower_bound: int = Field(..., ge=0, description="Lower bound estimate")
    upper_bound: int = Field(..., ge=0, description="Upper bound estimate")

    factors: ModelPredictionFactors = Field(
        default_factory=ModelPredictionFactors,
        description="Factors influencing prediction",
    )

    based_on: str = Field(..., description="Prediction methodology used")

    historical_accuracy: float | None = Field(
        None,
        description="Historical accuracy of similar predictions",
    )

    metadata: ModelPredictionMetadata | None = Field(
        default_factory=ModelPredictionMetadata,
        description="Additional prediction data",
    )

    def get_range(self) -> tuple[int, int]:
        """Get prediction range."""
        return (self.lower_bound, self.upper_bound)

    def is_high_confidence(self) -> bool:
        """Check if prediction has high confidence."""
        return self.confidence_score >= 0.8
