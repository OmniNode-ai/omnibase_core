"""
Effect Handler Type Enumeration.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Eliminates raw string handler types to prevent typo bugs and enable IDE completion.
"""

from enum import Enum


class EnumEffectHandlerType(str, Enum):
    """
    Enumeration of supported effect handler types.

    SINGLE SOURCE OF TRUTH for handler type values.
    IO config models use this enum directly as the discriminator field type.

    Using an enum instead of raw strings:
    - Prevents typos ("filesystem" vs "file_system")
    - Enables IDE autocompletion
    - Provides exhaustiveness checking
    - Centralizes handler type definitions
    - Preserves full type safety (no .value string extraction)

    Pydantic Serialization Note:
        Because EnumEffectHandlerType inherits from (str, Enum), Pydantic
        automatically serializes to the string value ("http", "db", etc.)
        when dumping to JSON/YAML. The discriminated union works because
        Pydantic compares the serialized string values during validation.
    """

    HTTP = "http"
    DB = "db"
    KAFKA = "kafka"
    FILESYSTEM = "filesystem"

    @classmethod
    def values(cls) -> list[str]:
        """Return all handler type values."""
        return [member.value for member in cls]
