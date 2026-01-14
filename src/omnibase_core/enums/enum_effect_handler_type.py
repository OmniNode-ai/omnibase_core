"""
Effect Handler Type Enumeration.

Eliminates raw string handler types to prevent typo bugs and enable IDE completion.
"""

from enum import Enum, unique
from typing import Never, NoReturn

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumEffectHandlerType(StrValueHelper, str, Enum):
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

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensures exhaustive handling of all enum values in match statements.

        This method enables static type checkers to verify that all enum values
        are handled in match/case statements. If a case is missing, mypy will
        report an error at the call site.

        Usage:
            match handler_type:
                case EnumEffectHandlerType.HTTP:
                    handle_http()
                case EnumEffectHandlerType.DB:
                    handle_db()
                case EnumEffectHandlerType.KAFKA:
                    handle_kafka()
                case EnumEffectHandlerType.FILESYSTEM:
                    handle_filesystem()
                case _ as unreachable:
                    EnumEffectHandlerType.assert_exhaustive(unreachable)

        Args:
            value: The unhandled enum value (typed as Never for exhaustiveness).

        Raises:
            AssertionError: Always raised if this code path is reached at runtime.
        """
        # error-ok: exhaustiveness check - enums cannot import models
        raise AssertionError(f"Unhandled enum value: {value}")


__all__ = ["EnumEffectHandlerType"]
