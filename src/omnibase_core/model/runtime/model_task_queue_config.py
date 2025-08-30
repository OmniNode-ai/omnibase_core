"""
Task Queue Configuration Models

Models for configuring the task queue service components.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelQueueManagerConfig(BaseModel):
    """Configuration for the queue manager component."""

    poll_interval: int = Field(5, description="Seconds between database polls", ge=1)
    max_batch_size: int = Field(
        50,
        description="Maximum tasks to fetch per poll",
        ge=1,
        le=1000,
    )
    retry_failed_after_hours: int = Field(
        24,
        description="Hours before retrying failed tasks",
        ge=1,
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "poll_interval": 5,
                "max_batch_size": 50,
                "retry_failed_after_hours": 24,
            },
        },
    )


class ModelDramatiqWorkerConfig(BaseModel):
    """Configuration for a Dramatiq worker group."""

    name: str = Field(..., description="Worker group name")
    processes: int = Field(2, description="Number of worker processes", ge=1)
    threads: int = Field(4, description="Threads per process", ge=1)
    queue_name: str | None = Field("default", description="Queue to consume from")
    log_level: str | None = Field("INFO", description="Logging level")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "default",
                "processes": 2,
                "threads": 4,
                "queue_name": "default",
                "log_level": "INFO",
            },
        },
    )


class ModelDramatiqMiddlewareConfig(BaseModel):
    """Configuration for Dramatiq middleware."""

    age_limit_ms: int = Field(
        3600000,
        description="Max message age in milliseconds",
        ge=0,
    )
    time_limit_ms: int = Field(
        600000,
        description="Max execution time in milliseconds",
        ge=0,
    )
    max_retries: int = Field(3, description="Maximum retry attempts", ge=0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "age_limit_ms": 3600000,
                "time_limit_ms": 600000,
                "max_retries": 3,
            },
        },
    )


class ModelDramatiqConfig(BaseModel):
    """Configuration for Dramatiq task processor."""

    workers: list[ModelDramatiqWorkerConfig] = Field(
        default_factory=list,
        description="Worker configurations",
    )
    middleware: ModelDramatiqMiddlewareConfig = Field(
        default_factory=ModelDramatiqMiddlewareConfig,
        description="Middleware configuration",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workers": [
                    {
                        "name": "default",
                        "processes": 2,
                        "threads": 4,
                        "queue_name": "default",
                    },
                    {
                        "name": "priority",
                        "processes": 1,
                        "threads": 2,
                        "queue_name": "priority",
                    },
                ],
                "middleware": {
                    "age_limit_ms": 3600000,
                    "time_limit_ms": 600000,
                    "max_retries": 3,
                },
            },
        },
    )


class ModelMonitoringConfig(BaseModel):
    """Configuration for service monitoring."""

    health_check_interval: int = Field(
        30,
        description="Seconds between health checks",
        ge=1,
    )
    worker_restart_threshold: int = Field(
        3,
        description="Failed checks before restart",
        ge=1,
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"health_check_interval": 30, "worker_restart_threshold": 3},
        },
    )


class ModelTaskQueueConfig(BaseModel):
    """Complete task queue service configuration."""

    queue_manager: ModelQueueManagerConfig = Field(
        default_factory=ModelQueueManagerConfig,
        description="Queue manager configuration",
    )
    dramatiq: ModelDramatiqConfig = Field(
        default_factory=ModelDramatiqConfig,
        description="Dramatiq configuration",
    )
    monitoring: ModelMonitoringConfig = Field(
        default_factory=ModelMonitoringConfig,
        description="Monitoring configuration",
    )
    database_url: str | None = Field(None, description="Database connection URL")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "queue_manager": {"poll_interval": 5, "max_batch_size": 50},
                "dramatiq": {
                    "workers": [{"name": "default", "processes": 2, "threads": 4}],
                },
                "monitoring": {"health_check_interval": 30},
                "database_url": "postgresql://user:pass@localhost/onex",
            },
        },
    )
