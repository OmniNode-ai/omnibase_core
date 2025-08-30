"""
Model for quota metadata.

Metadata for quota usage configuration.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelQuotaMetadata(BaseModel):
    """Metadata for quota usage."""

    optimization_enabled: bool = Field(
        True, description="Whether optimization is enabled"
    )
    auto_throttle: bool = Field(True, description="Whether auto-throttling is enabled")
    alert_email: Optional[str] = Field(None, description="Email for alerts")
    cost_center: Optional[str] = Field(None, description="Cost center for billing")
