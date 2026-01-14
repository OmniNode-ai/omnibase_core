"""
Data Type Enum.

Strongly typed data type values for configuration and processing.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDataType(StrValueHelper, str, Enum):
    """
    Strongly typed data type values.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    JSON = "json"
    XML = "xml"
    TEXT = "text"
    BINARY = "binary"
    CSV = "csv"
    YAML = "yaml"

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
