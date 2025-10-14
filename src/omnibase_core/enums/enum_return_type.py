from __future__ import annotations

import json

"""
Return Type Enum.

Strongly typed return type values for ONEX architecture output classification.
"""


from enum import Enum, unique


@unique
class EnumReturnType(str, Enum):
    """
    Strongly typed return type values for ONEX architecture.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support for return type validation operations.
    """

    MODELS = "MODELS"
    FILES = "FILES"
    REPORTS = "REPORTS"
    ENUMS = "ENUMS"
    TEXT = "TEXT"
    METADATA = "METADATA"
    BINARY = "BINARY"
    JSON = "JSON"
    XML = "XML"
    COMMANDS = "COMMANDS"
    NODES = "NODES"
    SCHEMAS = "SCHEMAS"
    PROTOCOLS = "PROTOCOLS"
    BACKEND = "BACKEND"
    RESULT = "RESULT"
    STATUS = "STATUS"
    LOGS = "LOGS"
    RESULTS = "RESULTS"
    UNKNOWN = "UNKNOWN"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_structured_data(cls, return_type: EnumReturnType) -> bool:
        """Check if the return type represents structured data."""
        return return_type in {
            cls.MODELS,
            cls.ENUMS,
            cls.METADATA,
            cls.JSON,
            cls.XML,
        }

    @classmethod
    def is_file_based(cls, return_type: EnumReturnType) -> bool:
        """Check if the return type represents file-based output."""
        return return_type in {
            cls.FILES,
            cls.REPORTS,
            cls.BINARY,
        }

    @classmethod
    def is_text_based(cls, return_type: EnumReturnType) -> bool:
        """Check if the return type represents text-based output."""
        return return_type in {
            cls.TEXT,
            cls.JSON,
            cls.XML,
            cls.REPORTS,
        }

    @classmethod
    def requires_serialization(cls, return_type: EnumReturnType) -> bool:
        """Check if the return type requires serialization."""
        return return_type in {
            cls.MODELS,
            cls.ENUMS,
            cls.METADATA,
            cls.JSON,
            cls.XML,
        }

    @classmethod
    def get_mime_type(cls, return_type: EnumReturnType) -> str:
        """Get the MIME type for a return type."""
        mime_types = {
            cls.JSON: "application/json",
            cls.XML: "application/xml",
            cls.TEXT: "text/plain",
            cls.BINARY: "application/octet-stream",
            cls.FILES: "application/octet-stream",
            cls.REPORTS: "text/plain",
            cls.MODELS: "application/json",
            cls.ENUMS: "application/json",
            cls.METADATA: "application/json",
        }
        return mime_types.get(return_type, "application/octet-stream")


# Export for use
__all__ = ["EnumReturnType"]
