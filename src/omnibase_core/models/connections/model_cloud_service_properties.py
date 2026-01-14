"""
Cloud service connection properties sub-model.

Part of the connection properties restructuring to reduce string field violations.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_instance_type import EnumInstanceType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import SerializedDict


class ModelCloudServiceProperties(BaseModel):
    """Cloud/service-specific connection properties.
    Implements Core protocols:
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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, TypeError, ValidationError, ValueError) as e:
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        # Pydantic handles validation automatically during instantiation.
        # This method exists to satisfy the ProtocolValidatable interface.
        return True

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


__all__ = ["ModelCloudServiceProperties"]
