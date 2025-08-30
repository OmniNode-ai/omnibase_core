"""
Service instance model for OmniMemory registry.

Represents a single service instance with its metadata and state.
"""

from typing import List

from pydantic import BaseModel, Field


class ModelServiceInstance(BaseModel):
    """Represents a service instance in the registry."""

    service_name: str = Field(..., description="Name of the service")
    service_type: str = Field(..., description="Type/class of the service")
    initialized: bool = Field(
        default=False, description="Whether the service is initialized"
    )
    dependencies: List[str] = Field(
        default_factory=list, description="List of service dependencies"
    )
    initialization_order: int = Field(
        ..., description="Order for service initialization"
    )
