"""
TypedDict for field values.

This supports the field accessor pattern by providing strong typing
for field values without resorting to Any type usage.
"""

from typing import TypedDict


class TypedDictFieldValue(TypedDict, total=False):
    """Typed dictionary for field values."""

    string_value: str
    int_value: int
    float_value: float
    bool_value: bool
    list_value: list[str]
