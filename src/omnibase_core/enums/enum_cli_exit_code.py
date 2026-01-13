"""CLI Exit Code Enumeration.

Standard CLI exit codes for ONEX operations.
"""

from enum import Enum, unique


@unique
class EnumCLIExitCode(int, Enum):
    """Standard CLI exit codes for ONEX operations.

    Exit Code Conventions:
    - 0: Success (EnumOnexStatus.SUCCESS)
    - 1: General error (EnumOnexStatus.ERROR, EnumOnexStatus.UNKNOWN)
    - 2: Warning (EnumOnexStatus.WARNING)
    - 3: Partial success (EnumOnexStatus.PARTIAL)
    - 4: Skipped (EnumOnexStatus.SKIPPED)
    - 5: Fixed (EnumOnexStatus.FIXED)
    - 6: Info (EnumOnexStatus.INFO)
    """

    SUCCESS = 0
    ERROR = 1
    WARNING = 2
    PARTIAL = 3
    SKIPPED = 4
    FIXED = 5
    INFO = 6


__all__ = ["EnumCLIExitCode"]
