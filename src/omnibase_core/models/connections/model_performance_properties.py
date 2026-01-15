"""
Performance connection properties sub-model.

Part of the connection properties restructuring to reduce string field violations.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import SerializedDict


class ModelPerformanceProperties(BaseModel):
    """Performance tuning connection properties.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Validatable: Validation and verification
    - Serializable: Data serialization/deserialization
    """

    # All performance settings are numeric, not string
    max_connections: int = Field(default=100, description="Maximum connections")
    connection_limit: int = Field(default=50, description="Connection limit")
    command_timeout: int = Field(default=30, description="Command timeout")

    # Compression and optimization settings
    enable_compression: bool = Field(
        default=False,
        description="Enable compression",
    )
    compression_level: int = Field(default=6, description="Compression level")
    enable_caching: bool = Field(default=True, description="Enable caching")

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
        """Validate instance integrity (ProtocolValidatable protocol)."""
        # Pydantic handles validation automatically during instantiation.
        # This method exists to satisfy the ProtocolValidatable interface.
        return True

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


__all__ = ["ModelPerformanceProperties"]
