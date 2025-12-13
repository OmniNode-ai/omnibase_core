"""
Registry Component Performance Model

Type-safe component performance tracking for registry health reporting.
"""

from pydantic import BaseModel, Field


class ModelRegistryComponentPerformance(BaseModel):
    """
    Type-safe component performance tracking for registry health.

    Tracks performance metrics for tools and services.
    """

    name: str = Field(
        default=..., description="Name of the component (tool or service)"
    )

    type: str = Field(
        default=..., description="Component type", pattern="^(tool|service)$"
    )

    category: str = Field(
        default=...,
        description="Component category (tool type or service type)",
    )

    response_time_ms: float = Field(
        default=...,
        description="Response time in milliseconds",
        ge=0,
    )

    status: str = Field(default=..., description="Current health status of component")
