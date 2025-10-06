from pydantic import Field

"""
Monitoring and observability configuration model.
"""

from pydantic import BaseModel, Field


class ModelMonitoringConfig(BaseModel):
    """Monitoring and observability configuration."""

    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(
        9090,
        description="Metrics endpoint port",
        ge=1024,
        le=65535,
    )
    tracing_enabled: bool = Field(
        default=False, description="Enable distributed tracing"
    )
    log_structured: bool = Field(default=True, description="Use structured logging")
    log_correlation_enabled: bool = Field(
        True,
        description="Enable log correlation IDs",
    )
