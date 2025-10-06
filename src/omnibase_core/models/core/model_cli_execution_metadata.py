from typing import Any

from pydantic import BaseModel, Field


class ModelCliExecutionMetadata(BaseModel):
    """Execution metadata for CLI commands."""

    # Command metadata
    command_source: str | None = Field(
        default=None,
        description="Source of command (user, script, api)",
    )
    command_version: str | None = Field(
        default=None,
        description="Version of CLI interface used",
    )
    command_group: str | None = Field(
        default=None, description="Command group/category"
    )

    # Execution environment
    host_name: str | None = Field(
        default=None, description="Host executing the command"
    )
    process_id: int | None = Field(default=None, description="Process ID of execution")
    thread_id: str | None = Field(default=None, description="Thread ID of execution")

    # Performance tracking
    queue_time_ms: int | None = Field(
        default=None,
        description="Time spent in queue before execution",
    )
    init_time_ms: int | None = Field(default=None, description="Initialization time")
    validation_time_ms: int | None = Field(
        default=None,
        description="Argument validation time",
    )

    # Resource usage
    memory_usage_mb: float | None = Field(
        default=None,
        description="Peak memory usage in MB",
    )
    cpu_usage_percent: float | None = Field(
        default=None,
        description="Average CPU usage percentage",
    )

    # Error tracking
    error_count: int = Field(default=0, description="Number of errors encountered")
    warning_count: int = Field(default=0, description="Number of warnings encountered")
    retry_count: int = Field(default=0, description="Number of retries performed")

    # Feature flags
    features_enabled: list[str] = Field(
        default_factory=list,
        description="Enabled feature flags",
    )
    features_disabled: list[str] = Field(
        default_factory=list,
        description="Disabled feature flags",
    )

    # Custom tags for filtering/grouping
    tags: dict[str, str] = Field(default_factory=dict, description="Custom tags")

    # Extensibility for command-specific data
    custom_metrics: dict[str, float] | None = Field(
        default=None,
        description="Command-specific metrics",
    )
    custom_properties: dict[str, str] | None = Field(
        default=None,
        description="Command-specific properties",
    )
