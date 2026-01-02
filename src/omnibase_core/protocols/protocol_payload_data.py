"""
Protocol for payload data with dict-like access.

This module provides the ProtocolPayloadData protocol which defines
the interface for compute pipeline data that needs dict-like access.
Compatible with dict, Pydantic BaseModel, and objects with __dict__.

Design Principles:
- Use typing.Protocol with @runtime_checkable for duck typing support
- Keep interfaces minimal - only define what Core actually needs
- Provide complete type hints for mypy strict mode compliance
- NO Any types - use object with proper constraints
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, TypeVar, overload, runtime_checkable

# Type variable for payload values - intentionally permissive for data payloads
PayloadValue = str | int | float | bool | None | list[object] | dict[str, object]

# Type variable for default values in get() method
_T = TypeVar("_T")


@runtime_checkable
class ProtocolPayloadData(Protocol):
    """
    Protocol for payload data with dict-like access.

    Defines the interface for compute pipeline data that needs dict-like access.
    Compatible with:
    - Python dict
    - Pydantic BaseModel (via model_dump)
    - Objects with __dict__ attribute

    This protocol enables type-safe access to payload data without using Any.

    Example:
        def process_payload(data: ProtocolPayloadData) -> None:
            if "user_id" in data:
                user_id = data["user_id"]
            for key in data.keys():
                print(f"{key}: {data.get(key)}")
    """

    @overload
    def get(self, key: str) -> PayloadValue | None:
        """Get value by key, returning None if not found."""
        ...

    @overload
    def get(self, key: str, default: _T) -> PayloadValue | _T:
        """Get value by key, returning default if not found."""
        ...

    def get(
        self, key: str, default: PayloadValue | _T | None = None
    ) -> PayloadValue | _T | None:
        """
        Get a value by key with optional default.

        Args:
            key: The key to look up
            default: Value to return if key not found

        Returns:
            The value associated with the key, or default if not found
        """
        ...

    def keys(self) -> Iterator[str]:
        """
        Return an iterator over the keys.

        Returns:
            Iterator of string keys
        """
        ...

    def values(self) -> Iterator[PayloadValue]:
        """
        Return an iterator over the values.

        Returns:
            Iterator of payload values
        """
        ...

    def items(self) -> Iterator[tuple[str, PayloadValue]]:
        """
        Return an iterator over (key, value) pairs.

        Returns:
            Iterator of (key, value) tuples
        """
        ...

    def __getitem__(self, key: str) -> PayloadValue:
        """
        Get value by key using bracket notation.

        Args:
            key: The key to look up

        Returns:
            The value associated with the key

        Raises:
            KeyError: If key is not found
        """
        ...

    def __contains__(self, key: object) -> bool:
        """
        Check if key exists in the payload.

        Args:
            key: The key to check

        Returns:
            True if key exists, False otherwise
        """
        ...


__all__ = ["ProtocolPayloadData", "PayloadValue"]
