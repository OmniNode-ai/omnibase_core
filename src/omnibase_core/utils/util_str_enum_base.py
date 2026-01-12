"""Mixin providing standard __str__ implementation for string enums."""

from __future__ import annotations


class StrValueMixin:
    """Mixin providing __str__ that returns self.value for str-based enums.

    Use with enums that inherit from (str, Enum) to provide consistent
    string serialization. The __str__ returns the enum's value directly.

    Example:
        class EnumExample(MixinEnumStr, str, Enum):
            VALUE_A = "value_a"
            VALUE_B = "value_b"

        str(EnumExample.VALUE_A)  # Returns: "value_a"
    """

    value: str  # Type hint for enum value

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
