"""
Base Collection Model.

Abstract base class for typed collections following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class BaseCollection(ABC, BaseModel):
    """Abstract base class for typed collections."""

    @abstractmethod
    def add_item(self, item: Any) -> None:
        """Add an item to the collection."""
        ...

    @abstractmethod
    def remove_item(self, item: Any) -> bool:
        """Remove an item from the collection."""
        ...

    @abstractmethod
    def get_item_count(self) -> int:
        """Get the number of items in the collection."""
        ...


# Export the model
__all__ = ["BaseCollection"]