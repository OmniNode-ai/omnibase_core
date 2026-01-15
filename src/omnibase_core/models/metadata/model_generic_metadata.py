from typing import overload
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.infrastructure.model_value import ModelValue
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    parse_semver_from_string,
)
from omnibase_core.protocols import ProtocolSupportedMetadataType
from omnibase_core.types.type_constraints import BasicValueType
from omnibase_core.types.typed_dict_metadata_dict import TypedDictMetadataDict


class ModelGenericMetadata(BaseModel):
    """
    Generic metadata storage with flexible fields.

    Implements Core-native protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

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
    custom_fields: dict[str, ModelValue] | None = Field(
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
        # For dict[str, Any]input, let Pydantic handle it
        return v

    @field_validator("custom_fields", mode="before")
    @classmethod
    def validate_custom_fields(cls, v: object) -> object:
        """Convert raw values to ModelValue objects."""
        if v is None:
            return v
        if isinstance(v, dict):
            result = {}
            for key, value in v.items():
                if isinstance(value, ModelValue):
                    result[key] = value
                elif (
                    isinstance(value, dict)
                    and "value_type" in value
                    and "raw_value" in value
                ):
                    # Deserialize from ModelValue dict representation
                    result[key] = ModelValue.model_validate(value)
                else:
                    # Convert raw values to ModelValue
                    result[key] = ModelValue.from_any(value)
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

    def get_field(self, key: str, default: object = None) -> object:
        """Get a custom field value with type safety."""
        if self.custom_fields is None:
            return default
        cli_value = self.custom_fields.get(key)
        if cli_value is None:
            return default

        # Handle ModelValue objects (custom_fields is typed as dict[str, ModelValue])
        # If custom_fields validation worked correctly, cli_value should always be ModelValue
        if hasattr(cli_value, "to_python_value"):
            return cli_value.to_python_value()
        # Fallback for edge cases where validation didn't convert properly
        # This branch should be rare if validation is working correctly
        return cli_value

    @overload
    def set_field(self, key: str, value: str) -> None: ...

    @overload
    def set_field(self, key: str, value: bool) -> None: ...

    @overload
    def set_field(self, key: str, value: int) -> None: ...

    @overload
    def set_field(self, key: str, value: float) -> None: ...

    @overload
    def set_field(self, key: str, value: list[object]) -> None: ...

    @overload
    def set_field(self, key: str, value: dict[str, object]) -> None: ...

    def set_field(self, key: str, value: object) -> None:
        """Set a custom field value with type validation."""
        # Validate that only supported types are used
        if not isinstance(value, (str, int, bool, float, list, dict)):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value must be str, int, bool, float, list, or dict. Got {type(value).__name__}",
                details=ModelErrorContext.with_context(
                    {
                        "key": ModelSchemaValue.from_value(key),
                        "value_type": ModelSchemaValue.from_value(str(type(value))),
                        "supported_types": ModelSchemaValue.from_value(
                            "str, int, bool, float, list, dict",
                        ),
                    },
                ),
            )
        if self.custom_fields is None:
            self.custom_fields = {}
        # ModelValue.from_any() handles type conversion for supported types
        self.custom_fields[key] = ModelValue.from_any(value)

    def get_typed_field(
        self,
        key: str,
        field_type: type[object],
        default: object,
    ) -> object:
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

    def set_typed_field(self, key: str, value: object) -> None:
        """Set a custom field value with runtime type validation."""
        if isinstance(value, ProtocolSupportedMetadataType):
            # Initialize custom_fields if needed
            if self.custom_fields is None:
                self.custom_fields = {}

            # Convert to ModelValue for strongly-typed storage
            if hasattr(value, "__dict__"):
                # For complex objects, store as string representation
                self.custom_fields[key] = ModelValue.from_string(str(value))
            # For primitive types, use ModelValue.from_any() for type-safe storage
            elif isinstance(value, (str, int, float, bool)):
                self.custom_fields[key] = ModelValue.from_any(value)
            else:
                self.custom_fields[key] = ModelValue.from_string(str(value))
        else:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value type {type(value)} not supported for metadata storage",
                details=ModelErrorContext.with_context(
                    {
                        "key": ModelSchemaValue.from_value(key),
                        "value_type": ModelSchemaValue.from_value(str(type(value))),
                        "supported_interface": ModelSchemaValue.from_value(
                            "ProtocolSupportedMetadataType",
                        ),
                    },
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

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        # TypedDict only has: name, description, version, tags, metadata
        # Convert types to match TypedDict expectations
        metadata: TypedDictMetadataDict = TypedDictMetadataDict(
            name=self.metadata_display_name or "",
            description=self.description or "",
            version=(
                self.version if self.version else ModelSemVer(major=0, minor=0, patch=0)
            ),
            tags=self.tags,
            metadata={},  # Will populate below
        )

        # Include custom fields in the metadata dict
        if self.custom_fields:
            from typing import cast

            from omnibase_core.types.type_serializable_value import SerializableValue

            # Cast to SerializableValue for type compatibility
            custom_fields_dict = cast(
                dict[str, SerializableValue],
                {
                    key: cli_value.to_python_value()
                    for key, cli_value in self.custom_fields.items()
                },
            )
            metadata["metadata"]["custom_fields"] = custom_fields_dict

        # Add metadata_id to metadata dict if present
        if self.metadata_id:
            metadata["metadata"]["metadata_id"] = str(self.metadata_id)

        return metadata

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            # TypedDict has: name, description, version, tags, metadata
            if "name" in metadata:
                self.metadata_display_name = metadata["name"]
            if "description" in metadata:
                self.description = metadata["description"]
            if "tags" in metadata and isinstance(metadata["tags"], list):
                self.tags = metadata["tags"]

            # Custom fields are in the metadata dict
            if "metadata" in metadata:
                meta_dict = metadata["metadata"]
                if isinstance(meta_dict, dict) and "custom_fields" in meta_dict:
                    custom_fields = meta_dict["custom_fields"]
                    if isinstance(custom_fields, dict):
                        for key, value in custom_fields.items():
                            if isinstance(value, (str, int, bool, float)):
                                self.set_field(key, value)
            return True
        except Exception:  # fallback-ok: protocol method must return bool, not raise
            return False

    def serialize(self) -> dict[str, BasicValueType]:
        """Serialize metadata to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate metadata integrity (ProtocolValidatable protocol)."""
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
                except (
                    Exception
                ):  # fallback-ok: version validation, return False on any error
                    return False

            # Validate custom fields if present
            if self.custom_fields:
                for key, cli_value in self.custom_fields.items():
                    if not key or len(key.strip()) == 0:
                        return False
                    try:
                        # Test that we can convert to python value
                        cli_value.to_python_value()
                    except (
                        Exception
                    ):  # fallback-ok: field conversion test, return False on any error
                        return False

            return True
        except Exception:  # fallback-ok: protocol method must return bool, not raise
            return False
