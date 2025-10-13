"""
Enum for checkpoint status.
Single responsibility: Centralized checkpoint status definitions.
"""

from enum import Enum


class EnumCheckpointStatus(str, Enum):
    """Status of workflow checkpoints."""

    ACTIVE = "active"
    COMPLETED = "completed"
    RESTORED = "restored"
    EXPIRED = "expired"
    CORRUPTED = "corrupted"
