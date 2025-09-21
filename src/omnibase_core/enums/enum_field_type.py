"""
Field type enumeration for metadata field information.

Provides strongly typed field types for metadata fields.
Follows ONEX one-enum-per-file naming conventions.
"""

from __future__ import annotations

from enum import Enum


class EnumFieldType(str, Enum):
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
    LIST = "list"
    DICT = "dict"
    SET = "set"

    # Optional versions
    OPTIONAL_STRING = "str | None"
    OPTIONAL_INTEGER = "int | None"
    OPTIONAL_FLOAT = "float | None"
    OPTIONAL_BOOLEAN = "bool | None"
    OPTIONAL_DATETIME = "datetime | None"
    OPTIONAL_UUID = "uuid | None"

    # Complex types
    JSON = "json"
    BYTES = "bytes"
    ANY = "any"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

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
        return "| None" in self.value or "None |" in self.value

    @property
    def base_type(self) -> EnumFieldType:
        """Get the base type (without optional)."""
        if not self.is_optional:
            return self

        # Map optional types to base types
        base_mapping = {
            self.OPTIONAL_STRING: self.STRING,
            self.OPTIONAL_INTEGER: self.INTEGER,
            self.OPTIONAL_FLOAT: self.FLOAT,
            self.OPTIONAL_BOOLEAN: self.BOOLEAN,
            self.OPTIONAL_DATETIME: self.DATETIME,
            self.OPTIONAL_UUID: self.UUID,
        }

        return base_mapping.get(self, self.STRING)


# Export for use
__all__ = ["EnumFieldType"]
