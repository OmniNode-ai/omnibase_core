"""
ModelMonitoringConfig

Monitoring and observability configuration.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelMonitoringConfig(BaseModel):
    """Monitoring and observability configuration."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    prometheus_enabled: bool = Field(
        default=True,
        description="Enable Prometheus metrics",
    )
    prometheus_port: int = Field(default=9090, description="Prometheus metrics port")

    jaeger_enabled: bool = Field(default=False, description="Enable Jaeger tracing")
    jaeger_endpoint: str | None = Field(default=None, description="Jaeger endpoint")

    sentry_enabled: bool = Field(
        default=False,
        description="Enable Sentry error tracking",
    )
    sentry_dsn: str | None = Field(default=None, description="Sentry DSN")
