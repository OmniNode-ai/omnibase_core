"""Pattern Kind Enum.

Defines pattern categories for pattern extraction operations.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumPatternKind(StrValueHelper, str, Enum):
    """Categories of extractable patterns from session data.

    Used by pattern extraction to categorize discovered patterns.
    """

    FILE_ACCESS = "file_access"
    """Co-access patterns, entry points, modification clusters."""

    ERROR = "error"
    """Error-prone files, error sequences, failure patterns."""

    ARCHITECTURE = "architecture"
    """Module boundaries, layers, structural patterns."""

    TOOL_USAGE = "tool_usage"
    """Tool sequences, preferences, success rates."""


__all__ = ["EnumPatternKind"]
