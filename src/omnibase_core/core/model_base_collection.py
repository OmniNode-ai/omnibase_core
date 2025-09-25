"""
Base Collection Model.

Abstract base class for typed collections following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, Iterator, TypeVar

from pydantic import BaseModel

# Generic type variable for the items this collection contains
T = TypeVar("T")


class BaseCollection(ABC, BaseModel, Generic[T]):
    """Abstract base class for typed collections."""

    @abstractmethod
    def add_item(self, item: T) -> None:
        """Add an item to the collection."""
        ...

    @abstractmethod
    def remove_item(self, item: T) -> bool:
        """Remove an item from the collection."""
        ...

    @abstractmethod
    def get_item_count(self) -> int:
        """Get the number of items in the collection."""
        ...

    @abstractmethod
    def iter_items(self) -> Iterator[T]:
        """Iterate over items in the collection."""
        ...

    @abstractmethod
    def get_items(self) -> list[T]:
        """Get all items as a list."""
        ...


# Export the model
__all__ = ["BaseCollection"]
