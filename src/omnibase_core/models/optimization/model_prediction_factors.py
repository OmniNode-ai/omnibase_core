"""
Model for prediction factors.

Factors influencing usage prediction.
"""

from pydantic import BaseModel, Field


class ModelPredictionFactors(BaseModel):
    """Factors influencing usage prediction."""

    historical_average: float = Field(0.0, description="Historical average weight")
    day_of_week: float = Field(0.0, description="Day of week weight")
    time_of_day: float = Field(0.0, description="Time of day weight")
    queue_depth: float = Field(0.0, description="Queue depth weight")
    recent_trend: float = Field(0.0, description="Recent trend weight")
    seasonal_adjustment: float = Field(0.0, description="Seasonal adjustment weight")
