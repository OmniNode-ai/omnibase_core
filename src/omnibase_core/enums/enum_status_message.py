# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Status Message Enum.

Strongly typed status message values for progress tracking.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumStatusMessage(UtilStrValueHelper, str, Enum):
    """Strongly typed status message values."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Export for use
__all__ = ["EnumStatusMessage"]
