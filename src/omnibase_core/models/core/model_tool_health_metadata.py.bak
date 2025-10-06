import json
from typing import Any

from pydantic import Field

"""
Model for tool health metadata.

Simple metadata model for tool health status with proper typing
while avoiding heavy dependencies from full ModelToolMetadata.
"""

from pydantic import BaseModel, Field

from .model_tool_health_metadata_config import ModelConfig


class ModelToolHealthMetadata(BaseModel):
    """
    Simple metadata model for tool health information.

    Provides basic health metadata without the complexity of
    full tool metadata to avoid circular dependencies.
    """

    # Basic tool information
    tool_version: str | None = Field(None, description="Tool version")
    tool_class: str | None = Field(None, description="Tool implementation class")
    module_path: str | None = Field(None, description="Tool module path")

    # Health-specific metadata
    health_check_method: str | None = Field(
        None,
        description="Method used for health check",
    )
    health_check_endpoint: str | None = Field(
        None,
        description="Health check endpoint if available",
    )

    # Status information
    error_count: int = Field(0, description="Number of recent errors")
    warning_count: int = Field(0, description="Number of recent warnings")
    last_error_message: str | None = Field(
        None,
        description="Most recent error message",
    )

    # Performance indicators
    average_response_time_ms: float | None = Field(
        None,
        description="Average response time in milliseconds",
    )
    success_rate_percentage: float | None = Field(
        None,
        description="Success rate as percentage (0-100)",
    )

    # Operational metadata
    uptime_seconds: float | None = Field(None, description="Tool uptime in seconds")
    restart_count: int = Field(0, description="Number of restarts")

    # Tags and categorization
    health_tags: list[str] = Field(
        default_factory=list,
        description="Health-related tags",
    )
