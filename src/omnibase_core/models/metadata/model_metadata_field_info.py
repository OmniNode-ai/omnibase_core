"""
Metadata Field Info Model

Restructured to reduce string field violations through composition.
Each sub-model handles a specific concern area.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ...enums.enum_field_type import EnumFieldType
from .model_field_identity import ModelFieldIdentity
from .model_field_validation_rules import ModelFieldValidationRules


class ModelMetadataFieldInfo(BaseModel):
    """
    Metadata field information model.

    Restructured using composition to organize properties by concern.
    Reduces string field count through logical grouping.
    """

    # Grouped properties by concern
    identity: ModelFieldIdentity = Field(
        ..., description="Field identity and naming information"
    )

    # Field properties (non-string)
    is_required: bool = Field(
        ...,
        description="Whether this field is required in metadata",
    )

    is_optional: bool = Field(
        ...,
        description="Whether this field is optional with defaults",
    )

    is_volatile: bool = Field(
        ...,
        description="Whether this field may change on stamping",
    )

    # Field type (enum instead of string)
    field_type: EnumFieldType = Field(
        default=EnumFieldType.STRING,
        description="Python type of the field",
    )

    default_value: str | int | float | bool | None = Field(
        default=None,
        description="Default value for optional fields (restricted to basic types)",
    )

    # Validation rules (grouped)
    validation: ModelFieldValidationRules = Field(
        default_factory=ModelFieldValidationRules,
        description="Validation rules for the field",
    )

    # Backward compatibility properties
    @property
    def name(self) -> str:
        """Backward compatibility for name."""
        return self.identity.name

    @property
    def field_name(self) -> str:
        """Backward compatibility for field_name."""
        return self.identity.field_name

    @property
    def description(self) -> str:
        """Backward compatibility for description."""
        return self.identity.description

    @property
    def validation_pattern(self) -> str | None:
        """Backward compatibility for validation_pattern."""
        return self.validation.validation_pattern

    @property
    def min_length(self) -> int | None:
        """Backward compatibility for min_length."""
        return self.validation.min_length

    @property
    def max_length(self) -> int | None:
        """Backward compatibility for max_length."""
        return self.validation.max_length

    # Factory methods for all metadata fields
    @classmethod
    def metadata_version(cls) -> ModelMetadataFieldInfo:
        """Metadata version field info."""
        identity = ModelFieldIdentity(
            name="METADATA_VERSION",
            field_name="metadata_version",
            description="Version of the metadata schema",
        )
        return cls(
            identity=identity,
            is_required=False,
            is_optional=True,
            is_volatile=False,
            field_type=EnumFieldType.STRING,
            default_value="0.1.0",
        )

    @classmethod
    def protocol_version(cls) -> ModelMetadataFieldInfo:
        """Protocol version field info."""
        identity = ModelFieldIdentity(
            name="PROTOCOL_VERSION",
            field_name="protocol_version",
            description="Version of the ONEX protocol",
        )
        return cls(
            identity=identity,
            is_required=False,
            is_optional=True,
            is_volatile=False,
            field_type=EnumFieldType.STRING,
            default_value="0.1.0",
        )

    @classmethod
    def name_field(cls) -> ModelMetadataFieldInfo:
        """Name field info."""
        identity = ModelFieldIdentity(
            name="NAME", field_name="name", description="Name of the node/tool"
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
            name="VERSION", field_name="version", description="Version of the node/tool"
        )
        return cls(
            identity=identity,
            is_required=False,
            is_optional=True,
            is_volatile=False,
            field_type=EnumFieldType.STRING,
            default_value="1.0.0",
        )

    @classmethod
    def uuid(cls) -> ModelMetadataFieldInfo:
        """UUID field info."""
        identity = ModelFieldIdentity(
            name="UUID", field_name="uuid", description="Unique identifier"
        )
        validation = ModelFieldValidationRules(
            validation_pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
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
        return cls(
            name="AUTHOR",
            field_name="author",
            is_required=True,
            is_optional=False,
            is_volatile=False,
            field_type="str",
            description="Author of the node/tool",
        )

    @classmethod
    def created_at(cls) -> ModelMetadataFieldInfo:
        """Created at field info."""
        return cls(
            name="CREATED_AT",
            field_name="created_at",
            is_required=True,
            is_optional=False,
            is_volatile=False,
            field_type="datetime",
            description="Creation timestamp",
        )

    @classmethod
    def last_modified_at(cls) -> ModelMetadataFieldInfo:
        """Last modified at field info."""
        return cls(
            name="LAST_MODIFIED_AT",
            field_name="last_modified_at",
            is_required=True,
            is_optional=False,
            is_volatile=True,
            field_type="datetime",
            description="Last modification timestamp",
        )

    @classmethod
    def hash(cls) -> ModelMetadataFieldInfo:
        """Hash field info."""
        return cls(
            name="HASH",
            field_name="hash",
            is_required=True,
            is_optional=False,
            is_volatile=True,
            field_type="str",
            description="Content hash",
            validation_pattern=r"^[0-9a-f]{64}$",
        )

    @classmethod
    def entrypoint(cls) -> ModelMetadataFieldInfo:
        """Entrypoint field info."""
        return cls(
            name="ENTRYPOINT",
            field_name="entrypoint",
            is_required=True,
            is_optional=False,
            is_volatile=False,
            field_type="str",
            description="Entrypoint URI",
        )

    @classmethod
    def namespace(cls) -> ModelMetadataFieldInfo:
        """Namespace field info."""
        return cls(
            name="NAMESPACE",
            field_name="namespace",
            is_required=True,
            is_optional=False,
            is_volatile=False,
            field_type="str",
            description="Node namespace",
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
        return cls(
            name=field_name.upper(),
            field_name=field_name.lower(),
            is_required=False,
            is_optional=True,
            is_volatile=False,
            field_type="str",
            description=f"Field: {field_name}",
        )

    def __str__(self) -> str:
        """String representation for current standards."""
        return self.field_name

    def __eq__(self, other: object) -> bool:
        """Equality comparison for current standards."""
        if isinstance(other, str):
            return self.field_name == other or self.name == other.upper()
        if isinstance(other, ModelMetadataFieldInfo):
            return self.name == other.name
        return False
