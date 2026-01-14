"""
Field type enumeration for metadata field information.

Provides strongly typed field types for metadata fields.
Follows ONEX one-enum-per-file naming conventions.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumFieldType(StrValueHelper, str, Enum):
    """
    Strongly typed field type for metadata field definitions.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    # Basic types
    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"

    # Date/time types
    DATETIME = "datetime"
    DATE = "date"
    TIME = "time"
    TIMESTAMP = "timestamp"

    # UUID and identifiers
    UUID = "uuid"
    UUID4 = "uuid4"

    # Collections
    LIST = "list[Any]"
    DICT = "dict[str, Any]"
    SET = "set"

    # Optional versions
    OPTIONAL_STRING = "str | none"
    OPTIONAL_INTEGER = "int | none"
    OPTIONAL_FLOAT = "float | none"
    OPTIONAL_BOOLEAN = "bool | none"
    OPTIONAL_DATETIME = "datetime | none"
    OPTIONAL_UUID = "uuid | none"

    # Complex types
    JSON = "json"
    BYTES = "bytes"
    ANY = "any"

    @classmethod
    def from_string(cls, value: str) -> EnumFieldType:
        """Convert string to field type with fallback handling."""
        # Direct mapping
        for field_type in cls:
            if field_type.value == value:
                return field_type

        # Common aliases
        aliases = {
            "string": cls.STRING,
            "text": cls.STRING,
            "number": cls.FLOAT,
            "numeric": cls.FLOAT,
            "bool": cls.BOOLEAN,
            "datetime": cls.DATETIME,
            "timestamp": cls.TIMESTAMP,
            "id": cls.UUID,
            "identifier": cls.UUID,
            "optional_str": cls.OPTIONAL_STRING,
            "optional_int": cls.OPTIONAL_INTEGER,
        }

        normalized = value.lower().strip()
        if normalized in aliases:
            return aliases[normalized]

        # Default fallback
        return cls.STRING

    @property
    def is_optional(self) -> bool:
        """Check if this is an optional field type."""
        return "| none" in self.value or "none |" in self.value

    @property
    def base_type(self) -> EnumFieldType:
        """Get the base type (without optional)."""
        if not self.is_optional:
            return self

        # Map optional types to base types
        base_mapping: dict[EnumFieldType, EnumFieldType] = {
            EnumFieldType.OPTIONAL_STRING: EnumFieldType.STRING,
            EnumFieldType.OPTIONAL_INTEGER: EnumFieldType.INTEGER,
            EnumFieldType.OPTIONAL_FLOAT: EnumFieldType.FLOAT,
            EnumFieldType.OPTIONAL_BOOLEAN: EnumFieldType.BOOLEAN,
            EnumFieldType.OPTIONAL_DATETIME: EnumFieldType.DATETIME,
            EnumFieldType.OPTIONAL_UUID: EnumFieldType.UUID,
        }

        return base_mapping.get(self, EnumFieldType.STRING)


# Export for use
__all__ = ["EnumFieldType"]
