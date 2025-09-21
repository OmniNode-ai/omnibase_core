"""
Generic collection management pattern for Omnibase Core.

This module provides a reusable, strongly-typed collection base class that
can replace ad-hoc collection operations found across Config, Data, and other domains.
"""

from datetime import UTC, datetime
from typing import (
    Any,
    Callable,
    Generic,
    Optional,
    TypeVar,
)
from uuid import UUID

from pydantic import BaseModel, Field

from ...protocols.protocol_collection_item import CollectionItem
from .model_generic_collection_summary import ModelGenericCollectionSummary

# More constrained TypeVar for collection items
T = TypeVar(
    "T", bound=BaseModel
)  # Keep BaseModel bound for now, can be made more specific


class ModelGenericCollection(BaseModel, Generic[T]):
    """
    Generic collection with type safety and common operations.

    This class provides a standardized way to manage collections of Pydantic models
    with common operations like adding, removing, filtering, and querying items.
    It replaces ad-hoc collection patterns found throughout the codebase.

    Type Parameters:
        T: The type of items stored in the collection (must be a BaseModel)
    """

    items: list[T] = Field(
        default_factory=list, description="Collection items with strong typing"
    )

    collection_name: str = Field(
        default="", description="Optional name for the collection"
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the collection was created",
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the collection was last modified",
    )

    def add_item(self, item: T) -> None:
        """
        Add an item to the collection.

        Args:
            item: The item to add to the collection
        """
        self.items.append(item)
        self.updated_at = datetime.now(UTC)

    def remove_item(self, item_id: UUID) -> bool:
        """
        Remove an item by ID if it has an 'id' attribute.

        Args:
            item_id: UUID of the item to remove

        Returns:
            True if an item was removed, False otherwise
        """
        for i, item in enumerate(self.items):
            if hasattr(item, "id") and item.id == item_id:
                del self.items[i]
                self.updated_at = datetime.now(UTC)
                return True
        return False

    def remove_item_by_index(self, index: int) -> bool:
        """
        Remove an item by index.

        Args:
            index: Index of the item to remove

        Returns:
            True if an item was removed, False if index is out of bounds
        """
        if 0 <= index < len(self.items):
            del self.items[index]
            self.updated_at = datetime.now(UTC)
            return True
        return False

    def get_item(self, item_id: UUID) -> Optional[T]:
        """
        Get an item by ID if it has an 'id' attribute.

        Args:
            item_id: UUID of the item to retrieve

        Returns:
            The item if found, None otherwise
        """
        for item in self.items:
            if hasattr(item, "id") and item.id == item_id:
                return item
        return None

    def get_item_by_name(self, name: str) -> Optional[T]:
        """
        Get an item by name if it has a 'name' attribute.

        Args:
            name: Name of the item to retrieve

        Returns:
            The item if found, None otherwise
        """
        for item in self.items:
            if hasattr(item, "name") and item.name == name:
                return item
        return None

    def get_item_by_index(self, index: int) -> Optional[T]:
        """
        Get an item by index with bounds checking.

        Args:
            index: Index of the item to retrieve

        Returns:
            The item if found, None if index is out of bounds
        """
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def filter_items(self, predicate: Callable[[T], bool]) -> list[T]:
        """
        Filter items by a predicate function.

        Args:
            predicate: Function that takes an item and returns True/False

        Returns:
            List of items that match the predicate
        """
        return [item for item in self.items if predicate(item)]

    def get_enabled_items(self) -> list[T]:
        """
        Get items that have enabled=True.

        Returns:
            List of enabled items (items without 'enabled' attribute are considered enabled)
        """
        return self.filter_items(lambda item: getattr(item, "enabled", True))

    def get_valid_items(self) -> list[T]:
        """
        Get items that have is_valid=True or valid=True.

        Returns:
            List of valid items (items without validation attributes are considered valid)
        """
        return self.filter_items(
            lambda item: getattr(item, "is_valid", True)
            and getattr(item, "valid", True)
        )

    def get_items_by_tag(self, tag: str) -> list[T]:
        """
        Get items that have a specific tag in their 'tags' attribute.

        Args:
            tag: Tag to search for

        Returns:
            List of items that have the specified tag
        """
        return self.filter_items(
            lambda item: hasattr(item, "tags") and tag in getattr(item, "tags", [])
        )

    def item_count(self) -> int:
        """
        Get total item count.

        Returns:
            Total number of items in the collection
        """
        return len(self.items)

    def enabled_item_count(self) -> int:
        """
        Get count of enabled items.

        Returns:
            Number of enabled items
        """
        return len(self.get_enabled_items())

    def valid_item_count(self) -> int:
        """
        Get count of valid items.

        Returns:
            Number of valid items
        """
        return len(self.get_valid_items())

    def clear_all(self) -> None:
        """Remove all items from the collection."""
        self.items.clear()
        self.updated_at = datetime.now(UTC)

    def sort_by_priority(self, reverse: bool = False) -> None:
        """
        Sort items by priority field if they have one.

        Args:
            reverse: If True, sort in descending order (highest priority first)
        """
        self.items.sort(key=lambda item: getattr(item, "priority", 0), reverse=reverse)
        self.updated_at = datetime.now(UTC)

    def sort_by_name(self, reverse: bool = False) -> None:
        """
        Sort items by name field if they have one.

        Args:
            reverse: If True, sort in descending order
        """
        self.items.sort(key=lambda item: getattr(item, "name", ""), reverse=reverse)
        self.updated_at = datetime.now(UTC)

    def sort_by_created_at(self, reverse: bool = False) -> None:
        """
        Sort items by created_at field if they have one.

        Args:
            reverse: If True, sort newest first
        """
        self.items.sort(
            key=lambda item: getattr(item, "created_at", datetime.min), reverse=reverse
        )
        self.updated_at = datetime.now(UTC)

    def get_item_names(self) -> list[str]:
        """
        Get list of all item names.

        Returns:
            List of names from items that have a 'name' attribute
        """
        return [item.name for item in self.items if hasattr(item, "name") and item.name]

    def has_item_with_name(self, name: str) -> bool:
        """
        Check if collection contains an item with the given name.

        Args:
            name: Name to search for

        Returns:
            True if an item with that name exists
        """
        return self.get_item_by_name(name) is not None

    def has_item_with_id(self, item_id: UUID) -> bool:
        """
        Check if collection contains an item with the given ID.

        Args:
            item_id: ID to search for

        Returns:
            True if an item with that ID exists
        """
        return self.get_item(item_id) is not None

    def get_summary(self) -> ModelGenericCollectionSummary:
        """
        Get collection summary with key metrics.

        Returns:
            Strongly-typed summary model with collection statistics
        """
        return ModelGenericCollectionSummary(
            collection_name=self.collection_name,
            total_items=self.item_count(),
            enabled_items=self.enabled_item_count(),
            valid_items=self.valid_item_count(),
            created_at=self.created_at,
            updated_at=self.updated_at,
            has_items=self.item_count() > 0,
        )

    def extend_items(self, items: list[T]) -> None:
        """
        Add multiple items to the collection.

        Args:
            items: List of items to add
        """
        self.items.extend(items)
        self.updated_at = datetime.now(UTC)

    def find_items(self, **kwargs: str | int | bool | float) -> list[T]:
        """
        Find items by attribute values.

        Args:
            **kwargs: Attribute name/value pairs to match

        Returns:
            List of items that match all specified attributes

        Example:
            collection.find_items(enabled=True, category="test")
        """

        def matches_all(item: T) -> bool:
            for attr_name, expected_value in kwargs.items():
                if not hasattr(item, attr_name):
                    return False
                if getattr(item, attr_name) != expected_value:
                    return False
            return True

        return self.filter_items(matches_all)

    def update_item(self, item_id: UUID, **updates: str | int | bool | float) -> bool:
        """
        Update an item's attributes by ID.

        Args:
            item_id: ID of the item to update
            **updates: Attribute name/value pairs to update

        Returns:
            True if item was found and updated, False otherwise
        """
        item = self.get_item(item_id)
        if item is None:
            return False

        for attr_name, value in updates.items():
            if hasattr(item, attr_name):
                setattr(item, attr_name, value)

        self.updated_at = datetime.now(UTC)
        return True

    @classmethod
    def create_empty(cls, collection_name: str = "") -> "ModelGenericCollection[T]":
        """
        Create an empty collection.

        Args:
            collection_name: Optional name for the collection

        Returns:
            Empty collection instance
        """
        return cls(collection_name=collection_name)

    @classmethod
    def create_from_items(
        cls, items: list[T], collection_name: str = ""
    ) -> "ModelGenericCollection[T]":
        """
        Create a collection from a list of items.

        Args:
            items: Initial items for the collection
            collection_name: Optional name for the collection

        Returns:
            Collection instance with the specified items
        """
        return cls(items=items, collection_name=collection_name)


# Export for use
__all__ = ["ModelGenericCollection"]
