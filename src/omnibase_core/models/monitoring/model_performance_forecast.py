"""
Model for performance forecast.

Performance forecast based on historical data.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelPerformanceForecast(BaseModel):
    """Performance forecast based on historical data."""

    forecast_id: str = Field(..., description="Unique forecast identifier")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Forecast creation time",
    )
    forecast_horizon_hours: int = Field(
        ...,
        gt=0,
        description="Forecast horizon in hours",
    )
    confidence_interval: float = Field(
        ...,
        ge=0,
        le=1,
        description="Confidence interval",
    )

    predicted_throughput: float = Field(0.0, ge=0, description="Predicted throughput")
    predicted_cost: float = Field(0.0, ge=0, description="Predicted cost")
    predicted_efficiency: float = Field(
        0.0,
        ge=0,
        le=100,
        description="Predicted efficiency",
    )

    throughput_lower_bound: float = Field(
        0.0,
        ge=0,
        description="Throughput lower bound",
    )
    throughput_upper_bound: float = Field(
        0.0,
        ge=0,
        description="Throughput upper bound",
    )

    cost_lower_bound: float = Field(0.0, ge=0, description="Cost lower bound")
    cost_upper_bound: float = Field(0.0, ge=0, description="Cost upper bound")

    model_accuracy: float = Field(
        0.0,
        ge=0,
        le=100,
        description="Historical model accuracy",
    )
    based_on_samples: int = Field(0, ge=0, description="Number of samples used")

    recommendations: list[str] = Field(
        default_factory=list,
        description="Forecast-based recommendations",
    )

    risk_factors: list[str] = Field(
        default_factory=list,
        description="Identified risk factors",
    )

    def is_high_confidence(self) -> bool:
        """Check if forecast has high confidence."""
        return self.confidence_interval >= 0.8 and self.model_accuracy >= 85.0
