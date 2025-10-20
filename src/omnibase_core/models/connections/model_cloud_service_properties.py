from __future__ import annotations

import uuid

from pydantic import Field

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Cloud service connection properties sub-model.

Part of the connection properties restructuring to reduce string field violations.
"""


from typing import Any
from uuid import UUID

from pydantic import BaseModel

from omnibase_core.enums.enum_instance_type import EnumInstanceType
from omnibase_core.errors.error_codes import EnumCoreErrorCode


class ModelCloudServiceProperties(BaseModel):
    """Cloud/service-specific connection properties.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Validatable: Validation and verification
    - Serializable: Data serialization/deserialization
    """

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

    # Protocol method implementations

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


__all__ = ["ModelCloudServiceProperties"]
