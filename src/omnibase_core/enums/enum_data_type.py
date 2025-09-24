"""
Data Type Enum.

Strongly typed data type values for configuration and processing.
"""

from __future__ import annotations

from enum import Enum


class EnumDataType(str, Enum):
    """
    Strongly typed data type values.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    JSON = "JSON"
    XML = "XML"
    TEXT = "TEXT"
    BINARY = "binary"
    CSV = "CSV"
    YAML = "YAML"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_structured(cls, data_type: EnumDataType) -> bool:
        """Check if the data type represents structured data."""
        return data_type in {cls.JSON, cls.XML, cls.CSV, cls.YAML}

    @classmethod
    def is_text_based(cls, data_type: EnumDataType) -> bool:
        """Check if the data type is text-based."""
        return data_type in {cls.JSON, cls.XML, cls.TEXT, cls.CSV, cls.YAML}

    @classmethod
    def supports_schema(cls, data_type: EnumDataType) -> bool:
        """Check if the data type supports schema validation."""
        return data_type in {cls.JSON, cls.XML, cls.YAML}


# Export for use
__all__ = ["EnumDataType"]
