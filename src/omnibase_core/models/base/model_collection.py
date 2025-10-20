from __future__ import annotations

from typing import Any, Generic, TypeVar

"""
Base Collection Model.

Abstract base class for typed collections following ONEX one-model-per-file
architecture.
"""


from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Iterator

# Generic type variable for the items this collection contains
T = TypeVar("T")


class ModelBaseCollection(ABC, BaseModel, Generic[T]):
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
        """Get all items as a list[Any]."""
        ...

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export the model
__all__ = ["ModelBaseCollection"]
