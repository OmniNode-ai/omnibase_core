"""
Registry Operational Summary Model

Type-safe operational summary for registry resolution monitoring.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelRegistryOperationalSummary(BaseModel):
    """
    Type-safe operational summary for registry resolution.

    Provides structured monitoring and reporting data.
    """

    resolution_id: Optional[str] = Field(
        None, description="Unique identifier for this resolution context"
    )

    dependency_mode: str = Field(..., description="Active dependency mode (mock/real)")

    complexity: str = Field(
        ...,
        description="Resolution complexity level",
        pattern="^(simple|moderate|complex|enterprise)$",
    )

    strategy: str = Field(
        "default",
        description="Resolution strategy",
        pattern="^(fast|comprehensive|failsafe|development|production|default)$",
    )

    external_services_count: int = Field(
        0, description="Number of external services configured", ge=0
    )

    tools_count: int = Field(0, description="Number of tools in collection", ge=0)

    estimated_time_seconds: int = Field(
        ..., description="Estimated resolution time in seconds", ge=1
    )

    cache_enabled: bool = Field(True, description="Whether caching is enabled")

    validation_enabled: bool = Field(True, description="Whether validation is enabled")

    health_score: float = Field(
        1.0, description="Health score (0.0 to 1.0)", ge=0.0, le=1.0
    )

    is_valid: bool = Field(True, description="Whether context is valid")

    created_at: Optional[str] = Field(
        None, description="ISO timestamp when context was created"
    )

    # Performance metrics
    cache_hit_rate: Optional[float] = Field(
        None, description="Cache hit rate percentage", ge=0.0, le=100.0
    )

    average_resolution_time_ms: Optional[float] = Field(
        None, description="Average resolution time in milliseconds"
    )

    total_resolutions: Optional[int] = Field(
        None, description="Total number of resolutions performed", ge=0
    )
