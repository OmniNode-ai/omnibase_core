# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
CLI Status Enum.

Strongly typed status values for CLI operations.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumCliStatus(UtilStrValueHelper, str, Enum):
    """Strongly typed status values for CLI operations."""

    SUCCESS = "success"
    FAILED = "failed"
    WARNING = "warning"
    RUNNING = "running"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


# Export for use
__all__ = ["EnumCliStatus"]
