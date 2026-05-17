# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Enum for pre-commit tool names.
Single responsibility: Centralized pre-commit tool name definitions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumPrecommitToolNames(UtilStrValueHelper, str, Enum):
    """Pre-commit tool names following ONEX enum-backed naming standards."""

    TOOL_IDEMPOTENCY_ASSERTION_CHECKER = "tool_idempotency_assertion_checker"


__all__ = ["EnumPrecommitToolNames"]
