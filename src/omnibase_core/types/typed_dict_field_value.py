"""
TypedDict for field values.

This supports the field accessor pattern by providing strong typing
for field values without resorting to Any type usage.
"""

from typing_extensions import TypedDict


class TypedDictFieldValue(TypedDict, total=False):
    """Typed dictionary for field values.

    Provides strong typing for field values in the field accessor pattern,
    supporting common data types (string, int, float, bool, list) without
    resorting to Any type usage.

    All fields are optional (total=False).
    """

    string_value: str
    int_value: int
    float_value: float
    bool_value: bool
    list_value: list[str]


__all__ = ["TypedDictFieldValue"]
