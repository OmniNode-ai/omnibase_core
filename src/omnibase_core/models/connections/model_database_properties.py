"""
Database connection properties sub-model.

Part of the connection properties restructuring to reduce string field violations.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import SerializedDict


class ModelDatabaseProperties(BaseModel):
    """Database-specific connection properties.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Validatable: Validation and verification
    - Serializable: Data serialization/deserialization
    """

    # Entity references with UUID + display name pattern
    database_id: UUID | None = Field(
        default=None,
        description="Database UUID reference",
    )
    database_display_name: str | None = Field(
        default=None,
        description="Database display name",
    )
    schema_id: UUID | None = Field(default=None, description="Schema UUID reference")
    schema_display_name: str | None = Field(
        default=None,
        description="Schema display name",
    )

    # Database configuration (non-string)
    charset: str | None = Field(default=None, description="Character set")
    collation: str | None = Field(default=None, description="Collation")

    def get_database_identifier(self) -> str | None:
        """Get database identifier for display purposes."""
        if self.database_display_name:
            return self.database_display_name
        if self.database_id:
            return str(self.database_id)
        return None

    def get_schema_identifier(self) -> str | None:
        """Get schema identifier for display purposes."""
        if self.schema_display_name:
            return self.schema_display_name
        if self.schema_id:
            return str(self.schema_id)
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
        """Validate instance integrity (ProtocolValidatable protocol)."""
        # Pydantic handles validation automatically during instantiation.
        # This method exists to satisfy the ProtocolValidatable interface.
        return True

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


__all__ = ["ModelDatabaseProperties"]
