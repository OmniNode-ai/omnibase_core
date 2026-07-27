# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Registry Status Enum.

Strongly typed status values for registry operations.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumRegistryStatus(UtilStrValueHelper, str, Enum):
    """Strongly typed registry status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    INITIALIZING = "initializing"
    MAINTENANCE = "maintenance"


# Export for use
__all__ = ["EnumRegistryStatus"]
