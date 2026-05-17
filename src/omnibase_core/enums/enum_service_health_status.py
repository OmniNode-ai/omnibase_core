# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumServiceHealthStatus(UtilStrValueHelper, str, Enum):
    """Standard service health status values."""

    REACHABLE = "reachable"
    UNREACHABLE = "unreachable"
    ERROR = "error"
    DEGRADED = "degraded"
    TIMEOUT = "timeout"
    AUTHENTICATING = "authenticating"
    MAINTENANCE = "maintenance"


__all__ = ["EnumServiceHealthStatus"]
