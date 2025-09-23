"""
Generic collection management pattern for Omnibase Core.

This module provides a reusable, strongly-typed collection base class that
can replace ad-hoc collection operations found across Config, Data, and other domains.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import (
    Generic,
    TypedDict,
    TypeVar,
)
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.infrastructure.model_result import Result

from .model_generic_collection_summary import ModelGenericCollectionSummary

# More constrained TypeVar for collection items
T = TypeVar(
    "T",
    bound=BaseModel,
)  # Keep BaseModel bound for now, can be made more specific


class TypedDictCollectionCreateKwargs(TypedDict, total=False):
    """Type-safe dictionary for collection creation parameters."""

    collection_display_name: str
    collection_id: UUID


class TypedDictCollectionFromItemsKwargs(TypedDict, total=False):
    """Type-safe dictionary for collection creation from items parameters."""

    items: list[BaseModel]  # Use BaseModel instead of unbound T
    collection_display_name: str
    collection_id: UUID


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
        default_factory=list,
        description="Collection items with strong typing",
    )

    collection_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the collection",
    )

    collection_display_name: str = Field(
        default="",
        description="Human-readable display name for the collection",
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

    def get_item(self, item_id: UUID) -> Result[T, str]:
        """
        Get an item by ID if it has an 'id' attribute.

        Args:
            item_id: UUID of the item to retrieve

        Returns:
            Result containing the item if found, or error message if not found
        """
        for item in self.items:
            if hasattr(item, "id") and item.id == item_id:
                return Result.ok(item)
        return Result.err(f"Item with ID {item_id} not found in collection")

    def get_item_by_name(self, name: str) -> Result[T, str]:
        """
        Get an item by name if it has a 'name' attribute.

        Args:
            name: Name of the item to retrieve

        Returns:
            Result containing the item if found, or error message if not found
        """
        for item in self.items:
            if hasattr(item, "name") and item.name == name:
                return Result.ok(item)
        return Result.err(f"Item with name '{name}' not found in collection")

    def get_item_by_index(self, index: int) -> Result[T, str]:
        """
        Get an item by index with bounds checking.

        Args:
            index: Index of the item to retrieve

        Returns:
            Result containing the item if found, or error message if index is out of bounds
        """
        if 0 <= index < len(self.items):
            return Result.ok(self.items[index])
        return Result.err(
            f"Index {index} out of bounds for collection of size {len(self.items)}"
        )

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
            and getattr(item, "valid", True),
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
            lambda item: hasattr(item, "tags") and tag in getattr(item, "tags", []),
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
            key=lambda item: getattr(item, "created_at", datetime.min),
            reverse=reverse,
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
        return self.get_item_by_name(name).is_ok()

    def has_item_with_id(self, item_id: UUID) -> bool:
        """
        Check if collection contains an item with the given ID.

        Args:
            item_id: ID to search for

        Returns:
            True if an item with that ID exists
        """
        return self.get_item(item_id).is_ok()

    def get_summary(self) -> ModelGenericCollectionSummary:
        """
        Get collection summary with key metrics.

        Returns:
            Strongly-typed summary model with collection statistics
        """
        return ModelGenericCollectionSummary(
            collection_id=self.collection_id,
            collection_display_name=self.collection_display_name,
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

    def find_items(self, **kwargs: ModelSchemaValue) -> list[T]:
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
                raw_expected = expected_value.to_value()
                if getattr(item, attr_name) != raw_expected:
                    return False
            return True

        return self.filter_items(matches_all)

    def update_item(self, item_id: UUID, **updates: ModelSchemaValue) -> bool:
        """
        Update an item's attributes by ID.

        Args:
            item_id: ID of the item to update
            **updates: Attribute name/value pairs to update

        Returns:
            True if item was found and updated, False otherwise
        """
        item_result = self.get_item(item_id)
        if item_result.is_err():
            return False

        item = item_result.unwrap()
        for attr_name, value in updates.items():
            if hasattr(item, attr_name):
                raw_value = value.to_value()
                setattr(item, attr_name, raw_value)

        self.updated_at = datetime.now(UTC)
        return True

    @classmethod
    def create_empty(
        cls,
        collection_display_name: str = "",
        collection_id: UUID | None = None,
    ) -> ModelGenericCollection[T]:
        """
        Create an empty collection.

        Args:
            collection_display_name: Human-readable display name for the collection
            collection_id: UUID | None for the collection (auto-generated if None)

        Returns:
            Empty collection instance
        """
        kwargs: TypedDictCollectionCreateKwargs = {
            "collection_display_name": collection_display_name,
        }
        if collection_id is not None:
            kwargs["collection_id"] = collection_id
        return cls(**kwargs)

    @classmethod
    def create_from_items(
        cls,
        items: list[T],
        collection_display_name: str = "",
        collection_id: UUID | None = None,
    ) -> ModelGenericCollection[T]:
        """
        Create a collection from a list of items.

        Args:
            items: Initial items for the collection
            collection_display_name: Human-readable display name for the collection
            collection_id: UUID | None for the collection (auto-generated if None)

        Returns:
            Collection instance with the specified items
        """
        # Bypass TypedDict due to invariance issues with list[T] vs list[BaseModel]
        if collection_id is not None:
            return cls(
                items=items,
                collection_display_name=collection_display_name,
                collection_id=collection_id,
            )
        return cls(
            items=items,
            collection_display_name=collection_display_name,
        )


# Export for use
__all__ = ["ModelGenericCollection"]
