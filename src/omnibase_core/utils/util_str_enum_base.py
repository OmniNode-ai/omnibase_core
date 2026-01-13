"""StrValueHelper mixin providing standard __str__ for string enums."""

from __future__ import annotations


class StrValueHelper:
    """Mixin providing __str__ that returns self.value for str-based enums.

    Use with enums that inherit from (str, Enum) to provide consistent
    string serialization. The __str__ returns the enum's value directly.

    Example:
        class EnumStatus(StrValueHelper, str, Enum):
            PENDING = "pending"
            RUNNING = "running"

        str(EnumStatus.PENDING)  # Returns: "pending"
    """

    value: str  # Type hint for enum value

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
