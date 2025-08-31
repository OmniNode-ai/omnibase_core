"""
Enum for pre-commit tool names.
Single responsibility: Centralized pre-commit tool name definitions.
"""

from enum import Enum


class EnumPrecommitToolNames(str, Enum):
    """Pre-commit tool names following ONEX enum-backed naming standards."""

    TOOL_IDEMPOTENCY_ASSERTION_CHECKER = "tool_idempotency_assertion_checker"
