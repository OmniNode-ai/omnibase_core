"""
Model for MCP service status response.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelServiceDetail(BaseModel):
    """Model for individual service details."""

    name: str = Field(description="Service name")
    url: str = Field(description="Service URL")
    status: str = Field(description="Service status")
    healthy: bool = Field(description="Service health status")
    details: Optional[dict] = Field(
        default=None, description="Additional service details"
    )


class ModelMCPServiceStatus(BaseModel):
    """Model for MCP service status response."""

    status: str = Field(description="Overall status")
    services: List[ModelServiceDetail] = Field(
        default_factory=list, description="Service details"
    )
    total_services: int = Field(description="Total number of services")
    healthy_services: int = Field(description="Number of healthy services")
