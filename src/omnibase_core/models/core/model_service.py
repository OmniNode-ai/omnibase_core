from uuid import UUID

"""
Service Model

Pydantic model for ONEX service instances.
"""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_service_config import ModelConfig

if TYPE_CHECKING:
    pass


class ModelService(BaseModel):
    """Service instance model for ONEX services."""

    service_id: UUID = Field(description="Unique identifier for service")
    service_name: str = Field(description="Name of the service")
    service_type: str = Field(description="Type/category of service")
    protocol_name: str | None = Field(
        default=None,
        description="Protocol interface name if applicable",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Service metadata and configuration",
    )
    health_status: str = Field(
        default="unknown",
        description="Current health status of service",
    )
