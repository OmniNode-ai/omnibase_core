"""
Enforcement Mode Enum

Enforcement strategy modes for resource limits and constraints.
"""

from enum import Enum


class EnumEnforcementMode(str, Enum):
    """
    Enforcement strategy modes for resource limits and constraints.

    Defines how strictly resource limits should be enforced.
    """

    HARD = "hard"
    SOFT = "soft"
    ADVISORY = "advisory"
    DISABLED = "disabled"

    def __str__(self) -> str:
        """Return the string value of the enforcement mode."""
        return self.value

    def is_blocking(self) -> bool:
        """Check if this mode blocks operations that exceed limits."""
        return self == self.HARD

    def allows_overrun(self) -> bool:
        """Check if this mode allows temporary limit overruns."""
        return self in [self.SOFT, self.ADVISORY]

    def provides_warnings(self) -> bool:
        """Check if this mode provides warning when limits are approached."""
        return self in [self.SOFT, self.ADVISORY]
