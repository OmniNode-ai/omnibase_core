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

    The model field accepts both enum values and arbitrary strings to allow
    extensibility for custom deregistration reasons not covered by the standard
    values (e.g., 'health_check_failure', 'resource_exhaustion').

    Attributes:
        SHUTDOWN: Node is shutting down gracefully.
        UPGRADE: Node is being upgraded to a new version.
        MANUAL: Administrator manually deregistered the contract.

    Example:
        >>> reason = EnumDeregistrationReason.SHUTDOWN
        >>> str(reason)
        'shutdown'
        >>> import json
        >>> json.dumps({"reason": reason})
        '{"reason": "shutdown"}'

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

        Returns:
            True for all standard reasons (SHUTDOWN, UPGRADE, MANUAL).
        """
        return self in {
            EnumDeregistrationReason.SHUTDOWN,
            EnumDeregistrationReason.UPGRADE,
            EnumDeregistrationReason.MANUAL,
        }


# Set of known planned deregistration reason string values (lowercase)
_PLANNED_REASON_VALUES: frozenset[str] = frozenset(
    {
        EnumDeregistrationReason.SHUTDOWN.value,
        EnumDeregistrationReason.UPGRADE.value,
        EnumDeregistrationReason.MANUAL.value,
    }
)


def is_planned_deregistration(reason: EnumDeregistrationReason | str) -> bool:
    """Check if a deregistration reason represents a planned deregistration.

    This function handles both EnumDeregistrationReason enum values and arbitrary
    string reasons. It is designed to work with ModelContractDeregisteredEvent.reason
    which accepts `EnumDeregistrationReason | str`.

    Planned deregistrations are expected scenarios where a node cleanly deregisters:
    - SHUTDOWN: Node shutting down gracefully
    - UPGRADE: Node being upgraded to a new version
    - MANUAL: Administrator manually deregistered

    Custom string reasons (not matching the standard enum values) are assumed to
    represent unplanned deregistrations (e.g., 'health_check_failure',
    'resource_exhaustion', 'crash_recovery').

    Args:
        reason: Either an EnumDeregistrationReason enum value or a string reason.

    Returns:
        True if the reason is a known planned deregistration reason
        (SHUTDOWN, UPGRADE, or MANUAL), False otherwise.

    Example:
        >>> is_planned_deregistration(EnumDeregistrationReason.SHUTDOWN)
        True
        >>> is_planned_deregistration("shutdown")
        True
        >>> is_planned_deregistration("health_check_failure")
        False

    .. versionadded:: 0.9.8
        Added to support mixed enum/string reason handling in
        ModelContractDeregisteredEvent.
    """
    if isinstance(reason, EnumDeregistrationReason):
        return reason.is_planned()

    # For string values, check if they match known planned reason values
    return reason.lower() in _PLANNED_REASON_VALUES


__all__ = ["EnumDeregistrationReason", "is_planned_deregistration"]
