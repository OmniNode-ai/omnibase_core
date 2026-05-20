# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumRegistryHealthStatus(UtilStrValueHelper, str, Enum):
    """Standard registry health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ERROR = "error"
    INITIALIZING = "initializing"
    MAINTENANCE = "maintenance"
    CRITICAL = "critical"


__all__ = ["EnumRegistryHealthStatus"]
