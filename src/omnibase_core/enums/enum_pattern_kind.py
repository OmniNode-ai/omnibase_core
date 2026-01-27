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

    TOOL_FAILURE = "tool_failure"
    """Recurring tool failures and recovery strategies.

    Distinct from TOOL_USAGE which tracks sequences, preferences, and success rates.
    TOOL_FAILURE specifically captures:
    - recurring_failure: Same tool failing repeatedly with similar context
    - failure_sequence: Chains of failures that follow predictable patterns
    - context_failure: Failures tied to specific file types, directories, or states
    - recovery_pattern: Successful recovery strategies after tool failures
    - failure_hotspot: Code locations that consistently trigger tool failures
    """


__all__ = ["EnumPatternKind"]
