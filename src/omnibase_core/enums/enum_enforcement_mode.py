"""
Enforcement Mode Enum

Enforcement strategy modes for resource limits and constraints.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumEnforcementMode(StrValueHelper, str, Enum):
    """
    Enforcement strategy modes for resource limits and constraints.

    Defines how strictly resource limits should be enforced.
    """

    HARD = "hard"
    SOFT = "soft"
    ADVISORY = "advisory"
    DISABLED = "disabled"

    def is_blocking(self) -> bool:
        """Check if this mode blocks operations that exceed limits."""
        return self == self.HARD

    def allows_overrun(self) -> bool:
        """Check if this mode allows temporary limit overruns."""
        return self in {self.SOFT, self.ADVISORY}

    def provides_warnings(self) -> bool:
        """Check if this mode provides warning when limits are approached."""
        return self in {self.SOFT, self.ADVISORY}
