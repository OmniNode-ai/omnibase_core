"""Deregistration reason enumeration for contract lifecycle events.

Defines standard reasons for contract deregistration in the ONEX framework.
Part of the contract registration subsystem (OMN-1651).
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDeregistrationReason(StrValueHelper, str, Enum):
    """Reasons for contract deregistration.

    Standard values for why a node deregisters its contract. These are used
    in ModelContractDeregisteredEvent to indicate the deregistration cause.

    Attributes:
        SHUTDOWN: Node is shutting down gracefully.
        UPGRADE: Node is being upgraded to a new version.
        MANUAL: Administrator manually deregistered the contract.

    Example:
        >>> reason = EnumDeregistrationReason.SHUTDOWN
        >>> str(reason)
        'shutdown'
        >>> reason.is_planned()
        True

    .. versionadded:: 0.9.8
        Added as part of OMN-1651 to replace hardcoded reason strings.
    """

    SHUTDOWN = "shutdown"
    """Node is shutting down gracefully."""

    UPGRADE = "upgrade"
    """Node is being upgraded to a new version."""

    MANUAL = "manual"
    """Administrator manually deregistered the contract."""

    def is_planned(self) -> bool:
        """Check if this reason represents a planned deregistration.

        Planned deregistrations include shutdown, upgrade, and manual removal.
        These are expected scenarios where the node cleanly deregisters.

        Note:
            All current enum values return True. This method exists for
            forward compatibility - future values (e.g., FAILURE, CRASH,
            TIMEOUT) would return False. Downstream consumers should use
            this method rather than hardcoding enum membership checks.

        Returns:
            True for planned reasons (SHUTDOWN, UPGRADE, MANUAL).
            Future unplanned reasons would return False.
        """
        return self in {
            EnumDeregistrationReason.SHUTDOWN,
            EnumDeregistrationReason.UPGRADE,
            EnumDeregistrationReason.MANUAL,
        }


__all__ = ["EnumDeregistrationReason"]
