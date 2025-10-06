from __future__ import annotations

"""
Context Type Enum.

Strongly typed context type values for configuration and processing.
"""


from enum import Enum, unique


@unique
class EnumContextType(str, Enum):
    """
    Strongly typed context type values.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    USER = "user"
    SYSTEM = "system"
    BATCH = "batch"
    INTERACTIVE = "interactive"
    API = "api"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_automated(cls, context_type: EnumContextType) -> bool:
        """Check if the context type represents automated processing."""
        return context_type in {cls.SYSTEM, cls.BATCH, cls.API}

    @classmethod
    def is_user_driven(cls, context_type: EnumContextType) -> bool:
        """Check if the context type is user-driven."""
        return context_type in {cls.USER, cls.INTERACTIVE}

    @classmethod
    def supports_real_time(cls, context_type: EnumContextType) -> bool:
        """Check if the context type supports real-time interaction."""
        return context_type in {cls.INTERACTIVE, cls.API}


# Export for use
__all__ = ["EnumContextType"]
