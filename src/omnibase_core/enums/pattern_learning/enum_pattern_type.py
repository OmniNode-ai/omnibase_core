"""Enumeration for learned pattern types.

Defines the classification types for patterns extracted by the learning system.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumPatternType"]


@unique
class EnumPatternType(StrValueHelper, str, Enum):
    """Type classification for learned patterns.

    Categorizes patterns by their domain and usage context.

    Example:
        .. code-block:: python

            from omnibase_core.enums.pattern_learning import EnumPatternType

            pattern_type = EnumPatternType.CODE_PATTERN

            if pattern_type == EnumPatternType.ERROR_PATTERN:
                # Handle error-related patterns differently
                apply_error_handling_rules(pattern)

    .. versionadded:: 0.9.8
    """

    CODE_PATTERN = "code_pattern"
    """Pattern extracted from code structure or style.

    Examples include coding conventions, architectural patterns,
    and implementation idioms discovered from successful workflows.
    """

    ERROR_PATTERN = "error_pattern"
    """Pattern related to error handling or failure modes.

    Includes exception handling strategies, error recovery patterns,
    and common failure scenarios to avoid.
    """

    WORKFLOW_PATTERN = "workflow_pattern"
    """Pattern describing workflow or process sequences.

    Captures successful task execution sequences, pipeline configurations,
    and orchestration patterns.
    """

    INTERACTION_PATTERN = "interaction_pattern"
    """Pattern from user or system interactions.

    Includes request/response patterns, API usage patterns,
    and inter-service communication patterns.
    """

    CONFIGURATION_PATTERN = "configuration_pattern"
    """Pattern related to configuration or settings.

    Captures successful configuration combinations, environment setups,
    and deployment configurations.
    """
