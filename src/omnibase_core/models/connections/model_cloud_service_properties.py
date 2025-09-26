"""
Cloud service connection properties sub-model.

Part of the connection properties restructuring to reduce string field violations.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_instance_type import EnumInstanceType


class ModelCloudServiceProperties(BaseModel):
    """Cloud/service-specific connection properties."""

    # Service entity reference with UUID + display name pattern
    service_id: UUID | None = Field(default=None, description="Service UUID reference")
    service_display_name: str | None = Field(
        default=None,
        description="Service display name",
    )

    # Cloud configuration (non-string where possible)
    region: str | None = Field(default=None, description="Cloud region")
    availability_zone: str | None = Field(default=None, description="Availability zone")
    instance_type: EnumInstanceType | None = Field(
        default=None,
        description="Instance type",
    )

    def get_service_identifier(self) -> str | None:
        """Get service identifier for display purposes."""
        if self.service_display_name:
            return self.service_display_name
        if self.service_id:
            return str(self.service_id)
        return None

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export the model
__all__ = ["ModelCloudServiceProperties"]
