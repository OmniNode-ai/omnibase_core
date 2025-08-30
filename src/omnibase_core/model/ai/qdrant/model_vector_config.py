"""
Vector configuration model for Qdrant collection setup.

This model defines vector configuration parameters for collections,
following ONEX canonical patterns with proper validation.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from omnibase_core.model.ai.qdrant.model_distance_metric import \
        ModelDistanceMetric


class ModelVectorConfig(BaseModel):
    """Model representing vector configuration for a collection."""

    size: int = Field(..., description="Vector dimension size")
    distance_metric: "ModelDistanceMetric" = Field(
        ..., description="Distance metric for similarity calculation"
    )
    hnsw_config: Optional[Dict[str, Any]] = Field(
        None, description="HNSW index configuration"
    )
    quantization_config: Optional[Dict[str, Any]] = Field(
        None, description="Vector quantization configuration"
    )

    @field_validator("size")
    @classmethod
    def validate_size(cls, v):
        if v <= 0 or v > 65536:
            raise ValueError("Vector size must be between 1 and 65536")
        return v
