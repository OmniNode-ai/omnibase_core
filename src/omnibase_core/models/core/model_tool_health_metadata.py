from pydantic import Field

"\nModel for tool health metadata.\n\nSimple metadata model for tool health status with proper typing\nwhile avoiding heavy dependencies from full ModelToolMetadata.\n"
from pydantic import BaseModel

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelToolHealthMetadata(BaseModel):
    """
    Simple metadata model for tool health information.

    Provides basic health metadata without the complexity of
    full tool metadata to avoid circular dependencies.
    """

    tool_version: ModelSemVer | None = Field(default=None, description="Tool version")
    tool_class: str | None = Field(
        default=None, description="Tool implementation class"
    )
    module_path: str | None = Field(default=None, description="Tool module path")
    health_check_method: str | None = Field(
        default=None, description="Method used for health check"
    )
    health_check_endpoint: str | None = Field(
        default=None, description="Health check endpoint if available"
    )
    error_level_count: int = Field(default=0, description="Number of recent errors")
    warning_count: int = Field(default=0, description="Number of recent warnings")
    last_error_message: str | None = Field(
        default=None, description="Most recent error message"
    )
    average_response_time_ms: float | None = Field(
        default=None, description="Average response time in milliseconds"
    )
    success_rate_percentage: float | None = Field(
        default=None, description="Success rate as percentage (0-100)"
    )
    uptime_seconds: float | None = Field(
        default=None, description="Tool uptime in seconds"
    )
    restart_count: int = Field(default=0, description="Number of restarts")
    health_tags: list[str] = Field(
        default_factory=list, description="Health-related tags"
    )
