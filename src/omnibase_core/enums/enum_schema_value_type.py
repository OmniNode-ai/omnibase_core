"""
Schema value type enumeration for schema validation.

Provides strongly typed schema value type values for schema type checking.
Follows ONEX one-enum-per-file naming conventions.
"""

from enum import Enum


class EnumSchemaValueType(str, Enum):
    """
    Strongly typed schema value type for schema validation.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"
    ANY = "any"
    UNION = "union"
    ENUM = "enum"
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    UUID = "uuid"
    EMAIL = "email"
    URL = "url"
    URI = "uri"
    BINARY = "binary"
    BASE64 = "base64"
    JSON = "json"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_primitive(cls, value_type: "EnumSchemaValueType") -> bool:
        """Check if the schema value type is primitive."""
        return value_type in {cls.STRING, cls.INTEGER, cls.FLOAT, cls.BOOLEAN, cls.NULL}

    @classmethod
    def is_complex(cls, value_type: "EnumSchemaValueType") -> bool:
        """Check if the schema value type is complex."""
        return value_type in {cls.ARRAY, cls.OBJECT, cls.UNION, cls.ENUM}

    @classmethod
    def is_string_based(cls, value_type: "EnumSchemaValueType") -> bool:
        """Check if the schema value type is string-based."""
        return value_type in {cls.STRING, cls.EMAIL, cls.URL, cls.URI, cls.UUID, cls.DATE, cls.DATETIME, cls.TIME}

    @classmethod
    def is_numeric(cls, value_type: "EnumSchemaValueType") -> bool:
        """Check if the schema value type is numeric."""
        return value_type in {cls.INTEGER, cls.FLOAT}

    @classmethod
    def is_temporal(cls, value_type: "EnumSchemaValueType") -> bool:
        """Check if the schema value type is temporal."""
        return value_type in {cls.DATE, cls.DATETIME, cls.TIME}

    @classmethod
    def is_binary_based(cls, value_type: "EnumSchemaValueType") -> bool:
        """Check if the schema value type is binary-based."""
        return value_type in {cls.BINARY, cls.BASE64}

    @classmethod
    def requires_validation(cls, value_type: "EnumSchemaValueType") -> bool:
        """Check if the schema value type requires special validation."""
        return value_type in {cls.EMAIL, cls.URL, cls.URI, cls.UUID, cls.DATE, cls.DATETIME, cls.TIME, cls.JSON}

    @classmethod
    def supports_constraints(cls, value_type: "EnumSchemaValueType") -> bool:
        """Check if the schema value type supports constraints."""
        return value_type not in {cls.NULL, cls.ANY}


# Export for use
__all__ = ["EnumSchemaValueType"]