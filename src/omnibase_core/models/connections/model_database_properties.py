"""
Database connection properties sub-model.

Part of the connection properties restructuring to reduce string field violations.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError


class ModelDatabaseProperties(BaseModel):
    """Database-specific connection properties.
    Implements omnibase_spi protocols:
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
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


__all__ = ["ModelDatabaseProperties"]
