from __future__ import annotations

"""
Function status enumeration for node operations.

Provides strongly typed status values for function lifecycle tracking.
Follows ONEX one-enum-per-file naming conventions.
"""


from enum import Enum, unique


@unique
class EnumFunctionStatus(str, Enum):
    """
    Strongly typed function status for node operations.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
    EXPERIMENTAL = "experimental"
    MAINTENANCE = "maintenance"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_available(cls, status: EnumFunctionStatus) -> bool:
        """Check if the function is available for use."""
        return status in {cls.ACTIVE, cls.EXPERIMENTAL}

    @classmethod
    def requires_warning(cls, status: EnumFunctionStatus) -> bool:
        """Check if the function status requires a warning."""
        return status in {cls.DEPRECATED, cls.EXPERIMENTAL, cls.MAINTENANCE}

    @classmethod
    def is_production_ready(cls, status: EnumFunctionStatus) -> bool:
        """Check if the function is production-ready."""
        return status == cls.ACTIVE


# Export for use
__all__ = ["EnumFunctionStatus"]
