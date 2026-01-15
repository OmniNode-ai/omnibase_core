"""
Reusable Pydantic validator utilities for common conversion patterns.

This module provides factory functions for creating field validators
that handle common type conversions while maintaining type safety.

These patterns are used extensively in ONEX models to ensure collections
are immutable after construction, supporting frozen Pydantic models.

Usage Example
-------------
The validators are designed for use with Pydantic's @field_validator decorator::

    from pydantic import BaseModel, ConfigDict, field_validator
    from omnibase_core.utils.util_validators import (
        convert_list_to_tuple,
        convert_dict_to_frozen_pairs,
    )

    class MyModel(BaseModel):
        model_config = ConfigDict(frozen=True)

        items: tuple[str, ...]
        properties: tuple[tuple[str, str], ...]

        @field_validator("items", mode="before")
        @classmethod
        def _convert_items(
            cls, v: list[str] | tuple[str, ...] | object
        ) -> tuple[str, ...]:
            return convert_list_to_tuple(v)

        @field_validator("properties", mode="before")
        @classmethod
        def _convert_properties(
            cls, v: dict[str, str] | tuple[tuple[str, str], ...] | object
        ) -> tuple[tuple[str, str], ...]:
            return convert_dict_to_frozen_pairs(v, sort_keys=True)

Technical Notes
---------------
- The `type: ignore[return-value]` comments are intentional and safe because:
  1. Input could already be a valid tuple (passthrough case)
  2. Pydantic validates the final field type after the validator runs
  3. This allows accepting pre-validated data without redundant conversion
- See PR #298 for context on replacing `Any` with `object` for stronger typing

Deterministic Ordering
----------------------
- `convert_dict_to_frozen_pairs` supports optional key sorting via `sort_keys=True`
- Sorted keys ensure deterministic ordering for consistent hashing and comparison
- Use `sort_keys=True` when model equality or hashing matters (e.g., properties)
- Use `sort_keys=False` when insertion order must be preserved (e.g., ordered metadata)
"""

from datetime import datetime
from typing import TypeVar

__all__ = [
    "convert_list_to_tuple",
    "convert_dict_to_frozen_pairs",
    "ensure_timezone_aware",
]

# Generic type variable for list/tuple element types
T = TypeVar("T")

# Generic type variables for dict key/value types
K = TypeVar("K")
V = TypeVar("V")


def convert_list_to_tuple(v: list[T] | tuple[T, ...] | object) -> tuple[T, ...]:
    """
    Convert a list to a tuple for deep immutability in frozen Pydantic models.

    This function is designed for use in Pydantic field validators to convert
    mutable list inputs to immutable tuples. It handles three cases:

    1. **list input**: Converts to tuple (primary use case from YAML/JSON)
    2. **tuple input**: Passes through unchanged (already immutable)
    3. **other input**: Passes through for Pydantic to validate/reject

    Args:
        v: The input value, typically from YAML/JSON deserialization or
           direct model construction. Expected to be a list, tuple, or
           an already-validated tuple that Pydantic will verify.

    Returns:
        A tuple containing the list elements, or the input unchanged if
        it's already a tuple or another type.

    Note:
        The `type: ignore[return-value]` is safe because Pydantic validates
        the final field type after the validator runs.

    Example:
        ::

            @field_validator("states", mode="before")
            @classmethod
            def _convert_states(
                cls, v: list[object] | tuple[object, ...] | object
            ) -> tuple[object, ...]:
                return convert_list_to_tuple(v)
    """
    if isinstance(v, list):
        return tuple(v)
    # NOTE(OMN-1302): Passthrough for already-valid tuple or Pydantic to reject invalid types.
    # Safe because Pydantic validates final field type after validator runs.
    return v  # type: ignore[return-value]


def convert_dict_to_frozen_pairs(
    v: dict[K, V] | tuple[tuple[K, V], ...] | object,
    *,
    sort_keys: bool = False,
) -> tuple[tuple[K, V], ...]:
    """
    Convert a dict to a tuple of tuples for deep immutability in frozen Pydantic models.

    This function is designed for use in Pydantic field validators to convert
    mutable dict inputs to immutable tuples of key-value pairs. It handles three cases:

    1. **dict input**: Converts to tuple of tuples (primary use case from YAML/JSON)
    2. **tuple input**: Passes through unchanged (already immutable)
    3. **other input**: Passes through for Pydantic to validate/reject

    Args:
        v: The input value, typically from YAML/JSON deserialization or
           direct model construction. Expected to be a dict, tuple of tuples,
           or an already-validated tuple that Pydantic will verify.
        sort_keys: If True, sort the dict items by key for deterministic ordering.
            This ensures consistent hashing and comparison of model instances.
            Defaults to False to preserve insertion order.

    Returns:
        A tuple of (key, value) tuples, or the input unchanged if it's
        already a tuple or another type.

    Note:
        The `type: ignore[return-value]` is safe because Pydantic validates
        the final field type after the validator runs.

    Example:
        ::

            # Without sorting (preserves insertion order)
            @field_validator("variables", mode="before")
            @classmethod
            def _convert_variables(
                cls, v: dict[str, str] | tuple[tuple[str, str], ...] | object
            ) -> tuple[tuple[str, str], ...]:
                return convert_dict_to_frozen_pairs(v)

            # With sorting (deterministic ordering)
            @field_validator("properties", mode="before")
            @classmethod
            def _convert_properties(
                cls, v: dict[str, str] | tuple[tuple[str, str], ...] | object
            ) -> tuple[tuple[str, str], ...]:
                return convert_dict_to_frozen_pairs(v, sort_keys=True)
    """
    if isinstance(v, dict):
        items = v.items()
        if sort_keys:
            return tuple(sorted(items))
        return tuple(items)
    # NOTE(OMN-1302): Passthrough for already-valid tuple or Pydantic to reject invalid types.
    # Safe because Pydantic validates final field type after validator runs.
    return v  # type: ignore[return-value]


def ensure_timezone_aware(v: datetime, field_name: str = "timestamp") -> datetime:
    """
    Ensure a datetime value is timezone-aware, rejecting naive datetimes.

    This function validates that a datetime has proper timezone info, catching
    both truly naive datetimes (tzinfo=None) and "effectively naive" datetimes
    where tzinfo exists but returns None for utcoffset().

    Designed for use in Pydantic field validators to enforce timezone-aware
    timestamps across all omnimemory models.

    Args:
        v: The datetime value to validate.
        field_name: Name of the field being validated (for error messages).

    Returns:
        The validated datetime, unchanged if valid.

    Raises:
        ValueError: If the datetime is naive or effectively naive.

    Example:
        ::

            @field_validator("timestamp")
            @classmethod
            def validate_timestamp(cls, v: datetime) -> datetime:
                return ensure_timezone_aware(v, "timestamp")

    Note:
        "Effectively naive" datetimes occur when tzinfo is set but utcoffset()
        returns None. This can happen with custom timezone implementations
        that don't properly define the offset.
    """
    if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
        # error-ok: ValueError appropriate for Pydantic field_validator boundary validation
        raise ValueError(
            f"{field_name} must be timezone-aware (use datetime.now(UTC) or include tzinfo). "
            f"Got naive or effectively naive datetime: {v}"
        )
    return v
