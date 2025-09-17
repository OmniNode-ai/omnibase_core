"""
Model for prediction metadata.

Metadata for usage prediction.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelPredictionMetadata(BaseModel):
    """Metadata for usage prediction."""

    model_version: str = Field("v1.0.0", description="Prediction model version")
    training_samples: int = Field(0, description="Number of training samples")
    feature_count: int = Field(0, description="Number of features used")
    last_updated: datetime | None = Field(None, description="Model last updated")
