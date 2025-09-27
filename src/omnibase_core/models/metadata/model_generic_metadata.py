"""
Generic metadata model for flexible data storage.
"""

from __future__ import annotations

# Import proper type with fallback mechanism from metadata package
from typing import TYPE_CHECKING, Generic, TypeVar, cast
from uuid import UUID

if TYPE_CHECKING:
    from . import ProtocolSupportedMetadataType
else:
    # Runtime fallback - will be dict[str, object] from __init__.py
    from . import ProtocolSupportedMetadataType

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.infrastructure.model_cli_value import ModelCliValue

from .model_semver import ModelSemVer, parse_semver_from_string

# Simple TypeVar constraint for metadata types
T = TypeVar("T", str, int, bool, float)


class ModelGenericMetadata(BaseModel, Generic[T]):
    """Generic metadata storage with flexible fields."""

    metadata_id: UUID | None = Field(
        default=None,
        description="UUID for metadata identifier",
    )
    metadata_display_name: str | None = Field(
        default=None,
        description="Human-readable metadata name",
        alias="name",
    )
    description: str | None = Field(
        default=None,
        description="Metadata description",
    )
    version: ModelSemVer | None = Field(
        default=None,
        description="Metadata version",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Metadata tags",
    )
    custom_fields: dict[str, ModelCliValue] | None = Field(
        default=None,
        description="Custom metadata fields with strongly-typed values",
    )

    @field_validator("version", mode="before")
    @classmethod
    def validate_version(cls, v: object) -> object:
        """Convert string versions to ModelSemVer objects."""
        if v is None:
            return v
        if isinstance(v, str):
            return parse_semver_from_string(v)
        if isinstance(v, ModelSemVer):
            return v
        # For dict input, let Pydantic handle it
        return v

    @field_validator("custom_fields", mode="before")
    @classmethod
    def validate_custom_fields(cls, v: object) -> object:
        """Convert raw values to ModelCliValue objects."""
        if v is None:
            return v
        if isinstance(v, dict):
            result = {}
            for key, value in v.items():
                if isinstance(value, ModelCliValue):
                    result[key] = value
                else:
                    # Convert raw values to ModelCliValue
                    result[key] = ModelCliValue.from_any(value)
            return result
        return v

    @property
    def name(self) -> str | None:
        """Convenience property for metadata_display_name."""
        return self.metadata_display_name

    @name.setter
    def name(self, value: str | None) -> None:
        """Convenience setter for metadata_display_name."""
        self.metadata_display_name = value

    def get_field(self, key: str, default: T | None = None) -> T | None:
        """Get a custom field value with type safety."""
        if self.custom_fields is None:
            return default
        cli_value = self.custom_fields.get(key)
        if cli_value is None:
            return default

        # Handle both ModelCliValue objects and raw values
        if hasattr(cli_value, "to_python_value"):
            return cast(T, cli_value.to_python_value())
        elif (
            isinstance(cli_value, dict)
            and "raw_value" in cli_value
            and "value_type" in cli_value
        ):
            # This looks like a serialized ModelCliValue that wasn't properly reconstructed
            # Extract the actual raw value from the nested structure
            raw_value_obj = cli_value["raw_value"]
            if hasattr(raw_value_obj, "to_value"):
                return cast(T, raw_value_obj.to_value())
            else:
                return cast(T, raw_value_obj)
        else:
            # Raw value - return as is
            return cast(T, cli_value)

    def set_field(self, key: str, value: T) -> None:
        """Set a custom field value with type validation."""
        if not isinstance(value, (str, int, bool, float, list)):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value must be str, int, bool, float, or list, got {type(value)}",
                details=ModelErrorContext.with_context(
                    {
                        "key": ModelSchemaValue.from_value(key),
                        "value_type": ModelSchemaValue.from_value(str(type(value))),
                        "expected_types": ModelSchemaValue.from_value(
                            "str, int, bool, float, list"
                        ),
                    }
                ),
            )
        if self.custom_fields is None:
            self.custom_fields = {}
        self.custom_fields[key] = ModelCliValue.from_any(value)

    def get_typed_field(self, key: str, field_type: type[T], default: T) -> T:
        """Get a custom field value with specific type checking."""
        if self.custom_fields is None:
            return default
        cli_value = self.custom_fields.get(key)
        if cli_value is None:
            return default
        python_value = cli_value.to_python_value()
        if isinstance(python_value, field_type):
            return python_value
        return default

    def set_typed_field(self, key: str, value: T) -> None:
        """Set a custom field value with runtime type validation."""
        if isinstance(value, ProtocolSupportedMetadataType):
            # Initialize custom_fields if needed
            if self.custom_fields is None:
                self.custom_fields = {}

            # Convert to ModelCliValue for strongly-typed storage
            if hasattr(value, "__dict__"):
                # For complex objects, store as string representation
                self.custom_fields[key] = ModelCliValue.from_string(str(value))
            # For primitive types, use ModelCliValue.from_any() for type-safe storage
            elif isinstance(value, (str, int, float, bool)):
                self.custom_fields[key] = ModelCliValue.from_any(value)
            else:
                self.custom_fields[key] = ModelCliValue.from_string(str(value))
        else:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value type {type(value)} not supported for metadata storage",
                details=ModelErrorContext.with_context(
                    {
                        "key": ModelSchemaValue.from_value(key),
                        "value_type": ModelSchemaValue.from_value(str(type(value))),
                        "supported_interface": ModelSchemaValue.from_value(
                            "ProtocolSupportedMetadataType"
                        ),
                    }
                ),
            )

    def has_field(self, key: str) -> bool:
        """Check if a custom field exists."""
        if self.custom_fields is None:
            return False
        return key in self.custom_fields

    def remove_field(self, key: str) -> bool:
        """Remove a custom field. Returns True if removed, False if not found."""
        if self.custom_fields is None:
            return False
        if key in self.custom_fields:
            del self.custom_fields[key]
            return True
        return False

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
