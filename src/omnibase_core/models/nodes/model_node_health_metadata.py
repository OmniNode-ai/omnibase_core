"""
Model for node health metadata.

Simple metadata model for node health status with proper typing
while avoiding heavy dependencies from full ModelNodeMetadata.
"""

from pydantic import BaseModel, Field


class ModelNodeHealthMetadata(BaseModel):
    """
    Simple metadata model for node health information.

    Provides basic health metadata without the complexity of
    full node metadata to avoid circular dependencies.
    """

    # Basic node information
    node_version: str | None = Field(None, description="Node version")
    node_class: str | None = Field(None, description="Node implementation class")
    module_path: str | None = Field(None, description="Node module path")

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
    uptime_seconds: float | None = Field(None, description="Node uptime in seconds")
    restart_count: int = Field(0, description="Number of restarts")

    # Tags and categorization
    health_tags: list[str] = Field(
        default_factory=list,
        description="Health-related tags",
    )

    class Config:
        """Pydantic configuration."""

        # Example for documentation
        json_schema_extra = {
            "example": {
                "node_version": "1.0.0",
                "node_class": "NodeFileGenerator",
                "module_path": "protocol.nodes.example.node_example",
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
            },
        }
