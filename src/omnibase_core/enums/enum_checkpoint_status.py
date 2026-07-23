# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Enum for checkpoint status.
Single responsibility: Centralized checkpoint status definitions.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumCheckpointStatus(UtilStrValueHelper, str, Enum):
    """Status of workflow checkpoints."""

    ACTIVE = "active"
    COMPLETED = "completed"
    RESTORED = "restored"
    EXPIRED = "expired"
    CORRUPTED = "corrupted"
