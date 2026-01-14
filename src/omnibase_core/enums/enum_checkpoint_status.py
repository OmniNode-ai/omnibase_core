"""
Enum for checkpoint status.
Single responsibility: Centralized checkpoint status definitions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCheckpointStatus(StrValueHelper, str, Enum):
    """Status of workflow checkpoints."""

    ACTIVE = "active"
    COMPLETED = "completed"
    RESTORED = "restored"
    EXPIRED = "expired"
    CORRUPTED = "corrupted"
