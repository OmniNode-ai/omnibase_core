"""
Service Resolution Result Model

Pydantic model for service resolution operation results.
"""

from typing import Optional

from pydantic import BaseModel, Field

from .model_service import ModelService


class ModelServiceResolutionResult(BaseModel):
    """Service resolution result model."""

    service_instance: ModelService = Field(description="Resolved service instance")
    service_name: str = Field(description="Name of resolved service")
    resolution_method: str = Field(description="Method used for resolution")
    protocol_type: Optional[str] = Field(
        default=None, description="Protocol type if resolved via protocol"
    )

    class Config:
        frozen = True
