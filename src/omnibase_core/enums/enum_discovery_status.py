# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Discovery status enumeration for ONEX tool discovery operations."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumDiscoveryStatus(UtilStrValueHelper, str, Enum):
    """Discovery status values for tool discovery operations."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    PARTIAL = "partial"
    CACHED = "cached"
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    COMPLETED = "completed"


__all__ = ["EnumDiscoveryStatus"]
