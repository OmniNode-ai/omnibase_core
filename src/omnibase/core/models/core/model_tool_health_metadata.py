"""
Model for tool health metadata.

Simple metadata model for tool health status with proper typing
while avoiding heavy dependencies from full ModelToolMetadata.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelToolHealthMetadata(BaseModel):
    """
    Simple metadata model for tool health information.

    Provides basic health metadata without the complexity of
    full tool metadata to avoid circular dependencies.
    """

    # Basic tool information
    tool_version: Optional[str] = Field(None, description="Tool version")
    tool_class: Optional[str] = Field(None, description="Tool implementation class")
    module_path: Optional[str] = Field(None, description="Tool module path")

    # Health-specific metadata
    health_check_method: Optional[str] = Field(
        None, description="Method used for health check"
    )
    health_check_endpoint: Optional[str] = Field(
        None, description="Health check endpoint if available"
    )

    # Status information
    error_count: int = Field(0, description="Number of recent errors")
    warning_count: int = Field(0, description="Number of recent warnings")
    last_error_message: Optional[str] = Field(
        None, description="Most recent error message"
    )

    # Performance indicators
    average_response_time_ms: Optional[float] = Field(
        None, description="Average response time in milliseconds"
    )
    success_rate_percentage: Optional[float] = Field(
        None, description="Success rate as percentage (0-100)"
    )

    # Operational metadata
    uptime_seconds: Optional[float] = Field(None, description="Tool uptime in seconds")
    restart_count: int = Field(0, description="Number of restarts")

    # Tags and categorization
    health_tags: List[str] = Field(
        default_factory=list, description="Health-related tags"
    )

    class Config:
        """Pydantic configuration."""

        # Example for documentation
        json_schema_extra = {
            "example": {
                "tool_version": "1.0.0",
                "tool_class": "ToolFileGenerator",
                "module_path": "protocol.tools.example.tool_example",
                "health_check_method": "introspection",
                "health_check_endpoint": None,
                "error_count": 0,
                "warning_count": 1,
                "last_error_message": None,
                "average_response_time_ms": 125.5,
                "success_rate_percentage": 99.2,
                "uptime_seconds": 3600.0,
                "restart_count": 0,
                "health_tags": ["stable", "production"],
            }
        }
