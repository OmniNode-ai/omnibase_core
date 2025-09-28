"""
Generic metadata model for flexible data storage.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar, Union, cast, overload

# ONEX-compliant metadata value type
MetadataValueType = TypeVar("MetadataValueType", str, int, bool, float)
from uuid import UUID

# FIXME: ProtocolSupportedMetadataType not available in omnibase_spi
# from omnibase_spi.protocols.types import ProtocolSupportedMetadataType
# Temporarily using Protocol metadata as replacement
# from omnibase_spi.protocols.types import (
#     ProtocolMetadata as ProtocolSupportedMetadataType,
# )

# Temporary placeholder for validation
ProtocolSupportedMetadataType = type("ProtocolSupportedMetadataType", (), {})
from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import (
    MetadataProvider,
    Serializable,
    Validatable,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.infrastructure.model_cli_value import ModelCliValue

from .model_semver import ModelSemVer

# Simple TypeVar constraint for metadata types
T = TypeVar("T", str, int, bool, float)


class ModelGenericMetadata(BaseModel, Generic[T]):
    """
    Generic metadata storage with flexible fields.

    Implements omnibase_spi protocols:
    - MetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    metadata_id: UUID | None = Field(
        default=None,
        description="UUID for metadata identifier",
    )
    metadata_display_name: str | None = Field(
        default=None,
        description="Human-readable metadata name",
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

    def get_field(self, key: str, default: T) -> T:
        """Get a custom field value with type safety."""
        if self.custom_fields is None:
            return default
        cli_value = self.custom_fields.get(key)
        if cli_value is None:
            return default
        return cast(T, cli_value.to_python_value())

    @overload
    def set_field(self, key: str, value: str) -> None: ...

    @overload
    def set_field(self, key: str, value: bool) -> None: ...

    @overload
    def set_field(self, key: str, value: int) -> None: ...

    @overload
    def set_field(self, key: str, value: float) -> None: ...

    def set_field(self, key: str, value: MetadataValueType) -> None:
        """Set a custom field value with type validation."""
        if not isinstance(value, (str, int, bool, float)):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value must be str, int, bool, or float, got {type(value)}",
                details=ModelErrorContext.with_context(
                    {
                        "key": ModelSchemaValue.from_value(key),
                        "value_type": ModelSchemaValue.from_value(str(type(value))),
                        "expected_types": ModelSchemaValue.from_value(
                            "str, int, bool, float"
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

    # Protocol method implementations

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata as dictionary (MetadataProvider protocol)."""
        metadata: dict[str, Any] = {
            "metadata_id": str(self.metadata_id) if self.metadata_id else None,
            "metadata_display_name": self.metadata_display_name,
            "description": self.description,
            "version": str(self.version) if self.version else None,
            "tags": self.tags,
        }

        # Include custom fields
        if self.custom_fields:
            custom_fields_dict: dict[str, Any] = {
                key: cli_value.to_python_value()
                for key, cli_value in self.custom_fields.items()
            }
            metadata["custom_fields"] = custom_fields_dict

        return metadata

    def set_metadata(self, metadata: dict[str, Any]) -> bool:
        """Set metadata from dictionary (MetadataProvider protocol)."""
        try:
            if "metadata_display_name" in metadata:
                self.metadata_display_name = metadata["metadata_display_name"]
            if "description" in metadata:
                self.description = metadata["description"]
            if "tags" in metadata and isinstance(metadata["tags"], list):
                self.tags = metadata["tags"]
            if "custom_fields" in metadata:
                custom_fields = metadata["custom_fields"]
                if isinstance(custom_fields, dict):
                    for key, value in custom_fields.items():
                        if isinstance(value, (str, int, bool, float)):
                            self.set_field(key, value)
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize metadata to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate metadata integrity (Validatable protocol)."""
        try:
            # Validate metadata display name if present
            if (
                self.metadata_display_name is not None
                and len(self.metadata_display_name.strip()) == 0
            ):
                return False

            # Validate version if present
            if self.version is not None:
                try:
                    # Basic version validation
                    if (
                        self.version.major < 0
                        or self.version.minor < 0
                        or self.version.patch < 0
                    ):
                        return False
                except Exception:
                    return False

            # Validate custom fields if present
            if self.custom_fields:
                for key, cli_value in self.custom_fields.items():
                    if not key or len(key.strip()) == 0:
                        return False
                    try:
                        # Test that we can convert to python value
                        cli_value.to_python_value()
                    except Exception:
                        return False

            return True
        except Exception:
            return False
