import uuid
from datetime import datetime

from pydantic import Field

"""
Metadata Field Info Model

Replaces EnumNodeMetadataField enum with a proper model that includes
field properties and categorization.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelMetadataFieldInfo(BaseModel):
    """
    Metadata field information model.

    Replaces the EnumNodeMetadataField enum to provide structured information
    about each metadata field including requirements and properties.
    """

    # Core fields (required)
    name: str = Field(
        default=...,
        description="Field name identifier (e.g., METADATA_VERSION)",
        pattern="^[A-Z][A-Z0-9_]*$",
    )

    field_name: str = Field(
        default=...,
        description="Actual field name in models (e.g., metadata_version)",
    )

    # Properties
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

    # Field metadata
    field_type: str = Field(
        default=...,
        description="Python type of the field (str, int, datetime, etc.)",
    )

    default_value: Any | None = Field(
        default=None,
        description="Default value for optional fields",
    )

    description: str = Field(
        default="",
        description="Human-readable description of the field",
    )

    # Validation metadata
    validation_pattern: str | None = Field(
        default=None,
        description="Regex pattern for string validation",
    )

    min_length: int | None = Field(
        default=None,
        description="Minimum length for string fields",
    )

    max_length: int | None = Field(
        default=None,
        description="Maximum length for string fields",
    )

    # Factory methods for all metadata fields
    @classmethod
    def METADATA_VERSION(cls) -> "ModelMetadataFieldInfo":
        """Metadata version field info."""
        return cls(
            name="METADATA_VERSION",
            field_name="metadata_version",
            is_required=False,
            is_optional=True,
            is_volatile=False,
            field_type="str",
            default_value="0.1.0",
            description="Version of the metadata schema",
        )

    @classmethod
    def PROTOCOL_VERSION(cls) -> "ModelMetadataFieldInfo":
        """Protocol version field info."""
        return cls(
            name="PROTOCOL_VERSION",
            field_name="protocol_version",
            is_required=False,
            is_optional=True,
            is_volatile=False,
            field_type="str",
            default_value="0.1.0",
            description="Version of the ONEX protocol",
        )

    @classmethod
    def NAME(cls) -> "ModelMetadataFieldInfo":
        """Name field info."""
        return cls(
            name="NAME",
            field_name="name",
            is_required=True,
            is_optional=False,
            is_volatile=False,
            field_type="str",
            description="Name of the node/tool",
        )

    @classmethod
    def VERSION(cls) -> "ModelMetadataFieldInfo":
        """Version field info."""
        return cls(
            name="VERSION",
            field_name="version",
            is_required=False,
            is_optional=True,
            is_volatile=False,
            field_type="str",
            default_value="1.0.0",
            description="Version of the node/tool",
        )

    @classmethod
    def UUID(cls) -> "ModelMetadataFieldInfo":
        """UUID field info."""
        return cls(
            name="UUID",
            field_name="uuid",
            is_required=True,
            is_optional=False,
            is_volatile=False,
            field_type="str",
            description="Unique identifier",
            validation_pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        )

    @classmethod
    def AUTHOR(cls) -> "ModelMetadataFieldInfo":
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
    def CREATED_AT(cls) -> "ModelMetadataFieldInfo":
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
    def LAST_MODIFIED_AT(cls) -> "ModelMetadataFieldInfo":
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
    def HASH(cls) -> "ModelMetadataFieldInfo":
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
    def ENTRYPOINT(cls) -> "ModelMetadataFieldInfo":
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
    def NAMESPACE(cls) -> "ModelMetadataFieldInfo":
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
    def get_all_fields(cls) -> list["ModelMetadataFieldInfo"]:
        """Get all metadata field info objects."""
        # This would include all fields - abbreviated for brevity
        return [
            cls.METADATA_VERSION(),
            cls.PROTOCOL_VERSION(),
            cls.NAME(),
            cls.VERSION(),
            cls.UUID(),
            cls.AUTHOR(),
            cls.CREATED_AT(),
            cls.LAST_MODIFIED_AT(),
            cls.HASH(),
            cls.ENTRYPOINT(),
            cls.NAMESPACE(),
            # ... add all other fields
        ]

    @classmethod
    def get_required_fields(cls) -> list["ModelMetadataFieldInfo"]:
        """Get all required metadata fields."""
        return [f for f in cls.get_all_fields() if f.is_required]

    @classmethod
    def get_optional_fields(cls) -> list["ModelMetadataFieldInfo"]:
        """Get all optional metadata fields."""
        return [f for f in cls.get_all_fields() if f.is_optional]

    @classmethod
    def get_volatile_fields(cls) -> list["ModelMetadataFieldInfo"]:
        """Get all volatile metadata fields."""
        return [f for f in cls.get_all_fields() if f.is_volatile]

    @classmethod
    def from_string(cls, field_name: str) -> "ModelMetadataFieldInfo":
        """Create ModelMetadataFieldInfo from string field name."""
        field_map = {
            "METADATA_VERSION": cls.METADATA_VERSION,
            "PROTOCOL_VERSION": cls.PROTOCOL_VERSION,
            "NAME": cls.NAME,
            "VERSION": cls.VERSION,
            "UUID": cls.UUID,
            "AUTHOR": cls.AUTHOR,
            "CREATED_AT": cls.CREATED_AT,
            "LAST_MODIFIED_AT": cls.LAST_MODIFIED_AT,
            "HASH": cls.HASH,
            "ENTRYPOINT": cls.ENTRYPOINT,
            "NAMESPACE": cls.NAMESPACE,
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

    def __eq__(self, other) -> bool:
        """Equality comparison for current standards."""
        if isinstance(other, str):
            return self.field_name == other or self.name == other.upper()
        if isinstance(other, ModelMetadataFieldInfo):
            return self.name == other.name
        return False
