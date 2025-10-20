from __future__ import annotations

from pydantic import BaseModel, Field


class ModelWorkflowConfiguration(BaseModel):
    """Structured workflow configuration settings."""

    checkpoint_enabled: bool = Field(
        default=True,
        description="Enable workflow checkpointing",
    )
    checkpoint_interval: int = Field(
        default=10,
        description="Checkpoint interval in steps",
    )
    error_handling_strategy: str = Field(
        default="stop_on_error",
        description="Error handling strategy",
    )
    monitoring_enabled: bool = Field(
        default=True,
        description="Enable workflow monitoring",
    )
    metrics_collection: bool = Field(
        default=True,
        description="Enable metrics collection",
    )
    notification_settings: dict[str, str] = Field(
        default_factory=dict,
        description="Notification configuration",
    )
    resource_limits: dict[str, str] = Field(
        default_factory=dict,
        description="Resource limit configuration",
    )
