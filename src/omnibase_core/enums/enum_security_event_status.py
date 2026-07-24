# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Security Event Status Enumeration.

Strongly typed enumeration for security event statuses.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumSecurityEventStatus(UtilStrValueHelper, str, Enum):
    """Enumeration for security event statuses."""

    # Success statuses
    SUCCESS = "success"
    COMPLETED = "completed"

    # Failure statuses
    FAILED = "failed"
    DENIED = "denied"
    ERROR = "error"

    # In-progress statuses
    PENDING = "pending"
    IN_PROGRESS = "in_progress"

    # Other statuses
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


__all__ = ["EnumSecurityEventStatus"]
