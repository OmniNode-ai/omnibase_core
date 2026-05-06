# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
EnumEnforcement — operational outcome tiers for ONEX hook/skill enforcement.

Used by ModelEnforcementScope to declare how strictly a hook or skill enforces
its scope contract. The four tiers compose with the overlay loader (OMN-9905):
overlays may downgrade but never upgrade (e.g. block -> warn is legal; warn ->
block requires explicit operator intent).

Failure posture rules (from OMN-9895 epic):
- observe: log-only — never surface to user, never fail CI.
- warn:    emit a user-visible warning, return success (exit 0).
- block:   raise / exit 2 on violation. Default for security hooks.
- fail-fast: abort the session entirely. Reserved for security-critical
             contracts where continuing would produce unsafe state.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumEnforcement(StrValueHelper, str, Enum):
    """
    Operational outcome tiers for enforcement-scope contracts.

    Hooks and skills declare an ``enforcement`` field using these values to
    control what happens when a scope predicate fires. The tiers are ordered
    by severity: observe < warn < block < fail-fast.

    Overlay composition semantics (OMN-9905):
        Overlays may *downgrade* enforcement (block -> warn, warn -> observe)
        to support tester/external-contributor profiles. Upgrades require
        explicit operator-level intent and are not auto-composed.

    Attributes:
        OBSERVE:    Log the event; never surface to user or fail CI.
        WARN:       Emit a user-visible warning; return success (exit 0).
        BLOCK:      Raise / exit 2 on violation. Default for security hooks.
        FAIL_FAST:  Abort the session entirely. Reserved for security-critical
                    contracts where continuation would produce unsafe state.

    Example:
        >>> EnumEnforcement.BLOCK.value
        'block'
        >>> EnumEnforcement.WARN < EnumEnforcement.BLOCK
        True
    """

    OBSERVE = "observe"
    """Log only. Never surfaces to user; never fails CI. For telemetry hooks."""

    WARN = "warn"
    """Emit a warning, return success. Suitable for advisory checks."""

    BLOCK = "block"
    """Raise / exit 2. Default enforcement for hard-block hooks."""

    FAIL_FAST = "fail-fast"
    """Abort session. Reserved for security-critical contract violations."""

    def severity(self) -> int:
        """Return numeric severity (higher = stricter) for overlay comparison."""
        _order = {
            EnumEnforcement.OBSERVE: 0,
            EnumEnforcement.WARN: 1,
            EnumEnforcement.BLOCK: 2,
            EnumEnforcement.FAIL_FAST: 3,
        }
        return _order[self]

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, EnumEnforcement):
            return NotImplemented
        return self.severity() < other.severity()

    def __le__(self, other: object) -> bool:
        if not isinstance(other, EnumEnforcement):
            return NotImplemented
        return self.severity() <= other.severity()

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, EnumEnforcement):
            return NotImplemented
        return self.severity() > other.severity()

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, EnumEnforcement):
            return NotImplemented
        return self.severity() >= other.severity()

    @classmethod
    def can_downgrade_to(
        cls, source: "EnumEnforcement", target: "EnumEnforcement"
    ) -> bool:
        """Return True if target is a legal overlay downgrade of source."""
        return target.severity() <= source.severity()


__all__ = ["EnumEnforcement"]
