"""
Model for quota metadata.

Metadata for quota usage configuration.
"""

from pydantic import BaseModel, Field


class ModelQuotaMetadata(BaseModel):
    """Metadata for quota usage."""

    optimization_enabled: bool = Field(
        True,
        description="Whether optimization is enabled",
    )
    auto_throttle: bool = Field(True, description="Whether auto-throttling is enabled")
    alert_email: str | None = Field(None, description="Email for alerts")
    cost_center: str | None = Field(None, description="Cost center for billing")
