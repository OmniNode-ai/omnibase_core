"""Enumeration for binding expression functions.

Defines the allowed pipe functions for operation binding expressions.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumBindingFunction(StrValueHelper, str, Enum):
    """
    Allowed pipe functions in binding expressions.

    These are the ONLY functions permitted in binding expression pipes
    like `${request.snapshot | to_json}`.

    Attributes:
        TO_JSON: Serialize a value to JSON string.
        FROM_JSON: Deserialize a JSON string to a value.
    """

    TO_JSON = "to_json"
    """Serialize a value to JSON string."""

    FROM_JSON = "from_json"
    """Deserialize a JSON string to a value."""


__all__ = ["EnumBindingFunction"]
