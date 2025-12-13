"""Model for managing list[Any]s of strings."""

from typing import Any

from pydantic import BaseModel, Field


class ModelStringList(BaseModel):
    """
    Strongly-typed collection for managing string list[Any]s.

    Replaces List[str] to comply with ONEX
    standards requiring specific typed models.
    """

    items: list[str] = Field(default_factory=list, description="List of string items")

    def add(self, item: str) -> None:
        """Add an item to the list[Any]."""
        self.items.append(item)

    def remove(self, item: str) -> bool:
        """Remove an item from the list[Any]."""
        if item in self.items:
            self.items.remove(item)
            return True
        return False

    def contains(self, item: str) -> bool:
        """Check if item is in the list[Any]."""
        return item in self.items

    def get_all(self) -> list[str]:
        """Get all items."""
        return self.items.copy()

    def get(self, index: int) -> str:
        """Get item at specific index."""
        return self.items[index]

    def count(self) -> int:
        """Get number of items."""
        return len(self.items)

    def clear(self) -> None:
        """Remove all items."""
        self.items.clear()

    def extend(self, other_items: list[str]) -> None:
        """Add multiple items."""
        self.items.extend(other_items)

    def to_list(self) -> list[str]:
        """Convert to list[Any]representation."""
        return self.items.copy()

    def __len__(self) -> int:
        """Support len() function."""
        return len(self.items)

    def __iter__(self) -> Any:
        """Support iteration."""
        return iter(self.items)

    def __getitem__(self, index: int) -> str:
        """Support index access."""
        return self.items[index]
