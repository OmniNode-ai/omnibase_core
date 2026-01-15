"""
Metadata Field Info Model

Restructured to reduce string field violations through composition.
Each sub-model handles a specific concern area.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_field_type import EnumFieldType
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.infrastructure.model_value import ModelValue
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.utils.util_uuid_utilities import uuid_from_string

from .model_field_identity import ModelFieldIdentity
from .model_field_validation_rules import ModelFieldValidationRules

# Default version constants
DEFAULT_METADATA_VERSION = ModelSemVer(major=0, minor=1, patch=0)
DEFAULT_PROTOCOL_VERSION = ModelSemVer(major=0, minor=1, patch=0)
DEFAULT_NODE_VERSION = ModelSemVer(major=1, minor=0, patch=0)


class ModelMetadataFieldInfo(BaseModel):
    """
    Metadata field information model.

    Restructured using composition to organize properties by concern.
    Reduces string field count through logical grouping.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Grouped properties by concern
    identity: ModelFieldIdentity = Field(
        default=...,
        description="Field identity and naming information",
    )

    # Field properties (non-string)
    is_required: bool = Field(
        default=...,
        description="Whether this field is required in metadata",
    )

    is_optional: bool = Field(
        default=...,
        description="Whether this field is optional with defaults",
    )

    is_volatile: bool = Field(
        default=...,
        description="Whether this field may change on stamping",
    )

    # Field type (enum instead of string)
    field_type: EnumFieldType = Field(
        default=EnumFieldType.STRING,
        description="Python type of the field",
    )

    default_value: ModelValue | None = Field(
        default=None,
        description="Default value for optional fields with strongly-typed values",
    )

    # Validation rules (grouped)
    validation: ModelFieldValidationRules = Field(
        default_factory=lambda: ModelFieldValidationRules(),
        description="Validation rules for the field",
    )

    # Factory methods for all metadata fields
    @classmethod
    def metadata_version(cls) -> ModelMetadataFieldInfo:
        """Metadata version field info."""
        identity = ModelFieldIdentity(
            identity_id=uuid_from_string("METADATA_VERSION", "identity"),
            identity_display_name="METADATA_VERSION",
            field_id=uuid_from_string("metadata_version", "field"),
            field_display_name="metadata_version",
            description="Version of the metadata schema",
        )
        return cls(
            identity=identity,
            is_required=False,
            is_optional=True,
            is_volatile=False,
            field_type=EnumFieldType.STRING,
            default_value=ModelValue.from_string(str(DEFAULT_METADATA_VERSION)),
        )

    @classmethod
    def protocol_version(cls) -> ModelMetadataFieldInfo:
        """Protocol version field info."""
        identity = ModelFieldIdentity(
            identity_id=uuid_from_string("PROTOCOL_VERSION", "identity"),
            identity_display_name="PROTOCOL_VERSION",
            field_id=uuid_from_string("protocol_version", "field"),
            field_display_name="protocol_version",
            description="Version of the ONEX protocol",
        )
        return cls(
            identity=identity,
            is_required=False,
            is_optional=True,
            is_volatile=False,
            field_type=EnumFieldType.STRING,
            default_value=ModelValue.from_string(str(DEFAULT_PROTOCOL_VERSION)),
        )

    @classmethod
    def name_field(cls) -> ModelMetadataFieldInfo:
        """Name field info."""
        identity = ModelFieldIdentity(
            identity_id=uuid_from_string("NAME", "identity"),
            identity_display_name="NAME",
            field_id=uuid_from_string("name", "field"),
            field_display_name="name",
            description="Name of the node/tool",
        )
        return cls(
            identity=identity,
            is_required=True,
            is_optional=False,
            is_volatile=False,
            field_type=EnumFieldType.STRING,
        )

    @classmethod
    def version(cls) -> ModelMetadataFieldInfo:
        """Version field info."""
        identity = ModelFieldIdentity(
            identity_id=uuid_from_string("VERSION", "identity"),
            identity_display_name="VERSION",
            field_id=uuid_from_string("version", "field"),
            field_display_name="version",
            description="Version of the node/tool",
        )
        return cls(
            identity=identity,
            is_required=False,
            is_optional=True,
            is_volatile=False,
            field_type=EnumFieldType.STRING,
            default_value=ModelValue.from_string(str(DEFAULT_NODE_VERSION)),
        )

    @classmethod
    def uuid(cls) -> ModelMetadataFieldInfo:
        """UUID field info."""
        identity = ModelFieldIdentity(
            identity_id=uuid_from_string("UUID", "identity"),
            identity_display_name="UUID",
            field_id=uuid_from_string("uuid", "field"),
            field_display_name="uuid",
            description="Unique identifier",
        )
        validation = ModelFieldValidationRules(
            validation_pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        )
        return cls(
            identity=identity,
            is_required=True,
            is_optional=False,
            is_volatile=False,
            field_type=EnumFieldType.UUID,
            validation=validation,
        )

    @classmethod
    def author(cls) -> ModelMetadataFieldInfo:
        """Author field info."""
        identity = ModelFieldIdentity(
            identity_id=uuid_from_string("AUTHOR", "identity"),
            identity_display_name="AUTHOR",
            field_id=uuid_from_string("author", "field"),
            field_display_name="author",
            description="Author of the node/tool",
        )
        return cls(
            identity=identity,
            is_required=True,
            is_optional=False,
            is_volatile=False,
            field_type=EnumFieldType.STRING,
        )

    @classmethod
    def created_at(cls) -> ModelMetadataFieldInfo:
        """Created at field info."""
        identity = ModelFieldIdentity(
            identity_id=uuid_from_string("CREATED_AT", "identity"),
            identity_display_name="CREATED_AT",
            field_id=uuid_from_string("created_at", "field"),
            field_display_name="created_at",
            description="Creation timestamp",
        )
        return cls(
            identity=identity,
            is_required=True,
            is_optional=False,
            is_volatile=False,
            field_type=EnumFieldType.DATETIME,
        )

    @classmethod
    def last_modified_at(cls) -> ModelMetadataFieldInfo:
        """Last modified at field info."""
        identity = ModelFieldIdentity(
            identity_id=uuid_from_string("LAST_MODIFIED_AT", "identity"),
            identity_display_name="LAST_MODIFIED_AT",
            field_id=uuid_from_string("last_modified_at", "field"),
            field_display_name="last_modified_at",
            description="Last modification timestamp",
        )
        return cls(
            identity=identity,
            is_required=True,
            is_optional=False,
            is_volatile=True,
            field_type=EnumFieldType.DATETIME,
        )

    @classmethod
    def hash(cls) -> ModelMetadataFieldInfo:
        """Hash field info."""
        identity = ModelFieldIdentity(
            identity_id=uuid_from_string("HASH", "identity"),
            identity_display_name="HASH",
            field_id=uuid_from_string("hash", "field"),
            field_display_name="hash",
            description="Content hash",
        )
        validation = ModelFieldValidationRules(validation_pattern=r"^[0-9a-f]{64}$")
        return cls(
            identity=identity,
            is_required=True,
            is_optional=False,
            is_volatile=True,
            field_type=EnumFieldType.STRING,
            validation=validation,
        )

    @classmethod
    def entrypoint(cls) -> ModelMetadataFieldInfo:
        """Entrypoint field info."""
        identity = ModelFieldIdentity(
            identity_id=uuid_from_string("ENTRYPOINT", "identity"),
            identity_display_name="ENTRYPOINT",
            field_id=uuid_from_string("entrypoint", "field"),
            field_display_name="entrypoint",
            description="Entrypoint URI",
        )
        return cls(
            identity=identity,
            is_required=True,
            is_optional=False,
            is_volatile=False,
            field_type=EnumFieldType.STRING,
        )

    @classmethod
    def namespace(cls) -> ModelMetadataFieldInfo:
        """Namespace field info."""
        identity = ModelFieldIdentity(
            identity_id=uuid_from_string("NAMESPACE", "identity"),
            identity_display_name="NAMESPACE",
            field_id=uuid_from_string("namespace", "field"),
            field_display_name="namespace",
            description="Node namespace",
        )
        return cls(
            identity=identity,
            is_required=True,
            is_optional=False,
            is_volatile=False,
            field_type=EnumFieldType.STRING,
        )

    @classmethod
    def get_all_fields(cls) -> list[ModelMetadataFieldInfo]:
        """Get all metadata field info objects."""
        # This would include all fields - abbreviated for brevity
        return [
            cls.metadata_version(),
            cls.protocol_version(),
            cls.name_field(),
            cls.version(),
            cls.uuid(),
            cls.author(),
            cls.created_at(),
            cls.last_modified_at(),
            cls.hash(),
            cls.entrypoint(),
            cls.namespace(),
            # ... add all other fields
        ]

    @classmethod
    def get_required_fields(cls) -> list[ModelMetadataFieldInfo]:
        """Get all required metadata fields."""
        return [f for f in cls.get_all_fields() if f.is_required]

    @classmethod
    def get_optional_fields(cls) -> list[ModelMetadataFieldInfo]:
        """Get all optional metadata fields."""
        return [f for f in cls.get_all_fields() if f.is_optional]

    @classmethod
    def get_volatile_fields(cls) -> list[ModelMetadataFieldInfo]:
        """Get all volatile metadata fields."""
        return [f for f in cls.get_all_fields() if f.is_volatile]

    @classmethod
    def from_string(cls, field_name: str) -> ModelMetadataFieldInfo:
        """Create ModelMetadataFieldInfo from string field name."""
        field_map = {
            "METADATA_VERSION": cls.metadata_version,
            "PROTOCOL_VERSION": cls.protocol_version,
            "NAME": cls.name_field,
            "VERSION": cls.version,
            "UUID": cls.uuid,
            "AUTHOR": cls.author,
            "CREATED_AT": cls.created_at,
            "LAST_MODIFIED_AT": cls.last_modified_at,
            "HASH": cls.hash,
            "ENTRYPOINT": cls.entrypoint,
            "NAMESPACE": cls.namespace,
            # ... add all fields
        }

        factory = field_map.get(field_name.upper())
        if factory:
            return factory()
        # Unknown field - create generic
        identity = ModelFieldIdentity(
            identity_id=uuid_from_string(field_name.upper(), "identity"),
            identity_display_name=field_name.upper(),
            field_id=uuid_from_string(field_name.lower(), "field"),
            field_display_name=field_name.lower(),
            description=f"Field: {field_name}",
        )
        return cls(
            identity=identity,
            is_required=False,
            is_optional=True,
            is_volatile=False,
            field_type=EnumFieldType.STRING,
        )

    def __str__(self) -> str:
        """String representation for current standards."""
        return (
            self.identity.field_display_name
            or f"field_{str(self.identity.field_id)[:8]}"
        )

    def __eq__(self, other: object) -> bool:
        """Equality comparison for current standards."""
        if isinstance(other, str):
            field_name = (
                self.identity.field_display_name
                or f"field_{str(self.identity.field_id)[:8]}"
            )
            identity_name = (
                self.identity.identity_display_name
                or f"identity_{str(self.identity.identity_id)[:8]}"
            )
            return field_name == other or identity_name == other.upper()
        if isinstance(other, ModelMetadataFieldInfo):
            return self.identity.identity_id == other.identity.identity_id
        return False

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        if self.identity.field_display_name:
            result["name"] = self.identity.field_display_name
        if self.identity.description:
            result["description"] = self.identity.description
        result["metadata"] = {
            "field_type": self.field_type.value,
            "is_required": self.is_required,
            "is_optional": self.is_optional,
            "is_volatile": self.is_volatile,
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol).

        Raises:
            ModelOnexError: If setting an attribute fails or validation error occurs
        """
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except ModelOnexError:
            raise  # Re-raise without double-wrapping
        except PYDANTIC_MODEL_ERRORS as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        # Pydantic handles validation automatically during instantiation.
        # This method exists to satisfy the ProtocolValidatable interface.
        # Override in specific models for custom validation.
        return True
