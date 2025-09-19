"""
Observability configuration model for nodes.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.nodes import EnumLoggingLevel


class ModelObservabilityConfig(BaseModel):
    """Observability configuration."""

    model_config = ConfigDict(extra="forbid")

    metrics_enabled: bool = Field(
        default=True,
        description="Enable metrics collection",
    )
    tracing_enabled: bool = Field(
        default=True,
        description="Enable distributed tracing",
    )
    logging_level: EnumLoggingLevel = Field(
        default=EnumLoggingLevel.INFO,
        description="Logging level",
    )
    health_check_endpoint: bool = Field(
        default=True,
        description="Enable health check endpoint",
    )
