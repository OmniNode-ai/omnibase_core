"""
Function status enumeration for node operations.

Provides strongly typed status values for function lifecycle tracking.
Follows ONEX one-enum-per-file naming conventions.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumFunctionStatus(StrValueHelper, str, Enum):
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
