"""
Generic Collection Model.

Provides type-safe, reusable collection patterns with proper generics support.
This model implements common collection operations while maintaining type safety
through bounded generics and proper TypeVar constraints.
"""

from typing import Any, Callable, Generic, Iterator, Protocol, TypeVar, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

# Type variables for generic collections
T = TypeVar("T")  # Item type
K = TypeVar("K")  # Key type
V = TypeVar("V")  # Value type
T_covariant = TypeVar("T_covariant", covariant=True)  # For read-only operations

# Bounded type variables
T_BaseModel = TypeVar("T_BaseModel", bound=BaseModel)  # Must be BaseModel
T_Identifiable = TypeVar("T_Identifiable", bound="Identifiable")  # Must have ID


class Identifiable(Protocol):
    """Protocol for objects that have an identifier."""

    def get_id(self) -> str | UUID:
        """Get the unique identifier for this object."""
        ...


class SearchableItem(Protocol[T_covariant]):
    """Protocol for items that can be searched."""

    def matches_criteria(self, criteria: dict[str, Any]) -> bool:
        """Check if item matches search criteria."""
        ...

    def get_search_fields(self) -> dict[str, Any]:
        """Get fields available for search."""
        ...


class ModelGenericCollection(BaseModel, Generic[T]):
    """
    Generic collection with type-safe operations.

    Provides a foundation for type-safe collections with common operations
    like filtering, mapping, and aggregation while preserving type information.
    """

    # Collection metadata
    collection_id: UUID = Field(default_factory=uuid4, description="Unique collection identifier")
    name: str | None = Field(default=None, description="Collection name")
    description: str | None = Field(default=None, description="Collection description")

    # Collection data
    items: list[T] = Field(default_factory=list, description="Collection items")

    # Collection properties
    max_size: int | None = Field(default=None, description="Maximum collection size")
    allow_duplicates: bool = Field(default=True, description="Allow duplicate items")

    # Metadata
    tags: list[str] = Field(default_factory=list, description="Collection tags")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode='after')
    def validate_constraints(self) -> 'ModelGenericCollection[T]':
        """Validate collection constraints."""
        if self.max_size is not None and len(self.items) > self.max_size:
            raise ValueError(f"Collection size {len(self.items)} exceeds maximum {self.max_size}")
        return self

    def add(self, item: T) -> bool:
        """
        Add an item to the collection.

        Args:
            item: Item to add

        Returns:
            True if item was added, False if rejected (duplicates, size limit)
        """
        # Check size limit
        if self.max_size is not None and len(self.items) >= self.max_size:
            return False

        # Check duplicates
        if not self.allow_duplicates and item in self.items:
            return False

        self.items.append(item)
        return True

    def remove(self, item: T) -> bool:
        """
        Remove an item from the collection.

        Args:
            item: Item to remove

        Returns:
            True if item was removed, False if not found
        """
        try:
            self.items.remove(item)
            return True
        except ValueError:
            return False

    def clear(self) -> None:
        """Clear all items from the collection."""
        self.items.clear()

    def size(self) -> int:
        """Get the number of items in the collection."""
        return len(self.items)

    def is_empty(self) -> bool:
        """Check if the collection is empty."""
        return len(self.items) == 0

    def contains(self, item: T) -> bool:
        """Check if the collection contains an item."""
        return item in self.items

    def get_by_index(self, index: int) -> T | None:
        """Get an item by index with bounds checking."""
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def filter(self, predicate: Callable[[T], bool]) -> "ModelGenericCollection[T]":
        """
        Filter items based on a predicate.

        Args:
            predicate: Function that returns True for items to keep

        Returns:
            New collection with filtered items
        """
        filtered_items = [item for item in self.items if predicate(item)]
        return self.__class__(
            name=f"{self.name}_filtered" if self.name else None,
            items=filtered_items,
            max_size=self.max_size,
            allow_duplicates=self.allow_duplicates,
            tags=self.tags.copy(),
            metadata=self.metadata.copy()
        )

    def map(self, mapper: Callable[[T], V]) -> "ModelGenericCollection[V]":
        """
        Map items to a new type.

        Args:
            mapper: Function to transform each item

        Returns:
            New collection with mapped items
        """
        mapped_items = [mapper(item) for item in self.items]
        # Create new collection with mapped type
        return ModelGenericCollection[V](
            name=f"{self.name}_mapped" if self.name else None,
            items=mapped_items,
            max_size=self.max_size,
            allow_duplicates=self.allow_duplicates,
            tags=self.tags.copy(),
            metadata=self.metadata.copy()
        )

    def reduce(self, reducer: Callable[[V, T], V], initial: V) -> V:
        """
        Reduce collection to a single value.

        Args:
            reducer: Function to combine accumulator and item
            initial: Initial value for the accumulator

        Returns:
            Reduced value
        """
        result = initial
        for item in self.items:
            result = reducer(result, item)
        return result

    def group_by(self, key_func: Callable[[T], K]) -> dict[K, "ModelGenericCollection[T]"]:
        """
        Group items by a key function.

        Args:
            key_func: Function to extract grouping key from item

        Returns:
            Dictionary mapping keys to collections
        """
        groups: dict[K, list[T]] = {}
        for item in self.items:
            key = key_func(item)
            if key not in groups:
                groups[key] = []
            groups[key].append(item)

        return {
            key: self.__class__(
                name=f"{self.name}_group_{key}" if self.name else None,
                items=items,
                max_size=self.max_size,
                allow_duplicates=self.allow_duplicates,
                tags=self.tags.copy(),
                metadata=self.metadata.copy()
            )
            for key, items in groups.items()
        }

    def sort(self, key_func: Callable[[T], Any] | None = None, reverse: bool = False) -> "ModelGenericCollection[T]":
        """
        Sort the collection.

        Args:
            key_func: Optional function to extract sort key from item
            reverse: Sort in descending order if True

        Returns:
            New sorted collection
        """
        if key_func is not None:
            sorted_items = sorted(self.items, key=key_func, reverse=reverse)
        else:
            # Add type constraint for sortable items
            sorted_items = sorted([item for item in self.items if hasattr(item, '__lt__')], reverse=reverse)

        return self.__class__(
            name=f"{self.name}_sorted" if self.name else None,
            items=sorted_items,
            max_size=self.max_size,
            allow_duplicates=self.allow_duplicates,
            tags=self.tags.copy(),
            metadata=self.metadata.copy()
        )

    def take(self, count: int) -> "ModelGenericCollection[T]":
        """
        Take the first n items.

        Args:
            count: Number of items to take

        Returns:
            New collection with first n items
        """
        taken_items = self.items[:count]
        return self.__class__(
            name=f"{self.name}_take_{count}" if self.name else None,
            items=taken_items,
            max_size=self.max_size,
            allow_duplicates=self.allow_duplicates,
            tags=self.tags.copy(),
            metadata=self.metadata.copy()
        )

    def skip(self, count: int) -> "ModelGenericCollection[T]":
        """
        Skip the first n items.

        Args:
            count: Number of items to skip

        Returns:
            New collection without first n items
        """
        skipped_items = self.items[count:]
        return self.__class__(
            name=f"{self.name}_skip_{count}" if self.name else None,
            items=skipped_items,
            max_size=self.max_size,
            allow_duplicates=self.allow_duplicates,
            tags=self.tags.copy(),
            metadata=self.metadata.copy()
        )

    def concat(self, other: "ModelGenericCollection[T]") -> "ModelGenericCollection[T]":
        """
        Concatenate with another collection.

        Args:
            other: Collection to concatenate with

        Returns:
            New collection with items from both collections
        """
        combined_items = self.items + other.items

        # Check size limit
        if self.max_size is not None and len(combined_items) > self.max_size:
            combined_items = combined_items[:self.max_size]

        return self.__class__(
            name=f"{self.name}_concat" if self.name else None,
            items=combined_items,
            max_size=self.max_size,
            allow_duplicates=self.allow_duplicates,
            tags=list(set(self.tags + other.tags)),  # Merge tags
            metadata={**self.metadata, **other.metadata}  # Merge metadata
        )

    def distinct(self) -> "ModelGenericCollection[T]":
        """
        Get distinct items from the collection.

        Returns:
            New collection with unique items
        """
        seen = set()
        distinct_items = []
        for item in self.items:
            if item not in seen:
                seen.add(item)
                distinct_items.append(item)

        return self.__class__(
            name=f"{self.name}_distinct" if self.name else None,
            items=distinct_items,
            max_size=self.max_size,
            allow_duplicates=False,  # Distinct collection doesn't allow duplicates
            tags=self.tags.copy(),
            metadata=self.metadata.copy()
        )

    def find(self, predicate: Callable[[T], bool]) -> T | None:
        """
        Find the first item matching a predicate.

        Args:
            predicate: Function that returns True for the target item

        Returns:
            First matching item or None
        """
        for item in self.items:
            if predicate(item):
                return item
        return None

    def count(self, predicate: Callable[[T], bool] | None = None) -> int:
        """
        Count items matching a predicate.

        Args:
            predicate: Optional function to filter items

        Returns:
            Number of matching items
        """
        if predicate is None:
            return len(self.items)
        return sum(1 for item in self.items if predicate(item))

    def any(self, predicate: Callable[[T], bool] | None = None) -> bool:
        """
        Check if any item matches a predicate.

        Args:
            predicate: Optional function to test items

        Returns:
            True if any item matches (or collection is non-empty if no predicate)
        """
        if predicate is None:
            return len(self.items) > 0
        return any(predicate(item) for item in self.items)

    def all(self, predicate: Callable[[T], bool]) -> bool:
        """
        Check if all items match a predicate.

        Args:
            predicate: Function to test items

        Returns:
            True if all items match the predicate
        """
        return all(predicate(item) for item in self.items)

    def to_list(self) -> list[T]:
        """Convert to a regular Python list."""
        return self.items.copy()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "collection_id": str(self.collection_id),
            "name": self.name,
            "description": self.description,
            "items": self.items,
            "size": len(self.items),
            "max_size": self.max_size,
            "allow_duplicates": self.allow_duplicates,
            "tags": self.tags,
            "metadata": self.metadata
        }

    def __iter__(self) -> Iterator[T]:  # type: ignore[override]
        """Make collection iterable."""
        return iter(self.items)

    def __len__(self) -> int:
        """Get collection size."""
        return len(self.items)

    def __contains__(self, item: T) -> bool:
        """Check if collection contains an item."""
        return item in self.items

    def __getitem__(self, index: int) -> T:
        """Get item by index."""
        return self.items[index]

    def __setitem__(self, index: int, item: T) -> None:
        """Set item by index."""
        self.items[index] = item

    def __delitem__(self, index: int) -> None:
        """Delete item by index."""
        del self.items[index]


class ModelIdentifiableCollection(ModelGenericCollection[T]):
    """
    Collection for items that have identifiers.

    Provides additional methods for ID-based operations while maintaining
    type safety for identifiable objects.
    """

    model_config = {"arbitrary_types_allowed": True}

    def get_by_id(self, item_id: str | UUID) -> T | None:
        """
        Get an item by its identifier.

        Args:
            item_id: The identifier to search for

        Returns:
            Item with matching ID or None
        """
        item_id_str = str(item_id)
        for item in self.items:
            if hasattr(item, 'get_id') and str(item.get_id()) == item_id_str:
                return item
        return None

    def remove_by_id(self, item_id: str | UUID) -> bool:
        """
        Remove an item by its identifier.

        Args:
            item_id: The identifier of the item to remove

        Returns:
            True if item was removed, False if not found
        """
        item = self.get_by_id(item_id)
        if item is not None:
            return self.remove(item)
        return False

    def has_id(self, item_id: str | UUID) -> bool:
        """
        Check if collection contains an item with the given ID.

        Args:
            item_id: The identifier to check for

        Returns:
            True if item with ID exists
        """
        return self.get_by_id(item_id) is not None

    def get_all_ids(self) -> list[str]:
        """Get all identifiers in the collection."""
        return [str(item.get_id()) for item in self.items if hasattr(item, 'get_id')]

    def ensure_unique_ids(self) -> bool:
        """
        Check if all items have unique identifiers.

        Returns:
            True if all IDs are unique
        """
        ids = self.get_all_ids()
        return len(ids) == len(set(ids))


class ModelSearchableCollection(ModelGenericCollection[T]):
    """
    Collection with advanced search capabilities.

    Provides type-safe search operations for collections of searchable items.
    """

    model_config = {"arbitrary_types_allowed": True}

    def search(self, criteria: dict[str, Any]) -> "ModelSearchableCollection[T]":
        """
        Search for items matching criteria.

        Args:
            criteria: Search criteria dictionary

        Returns:
            New collection with matching items
        """
        def matches_criteria(item: T) -> bool:
            if hasattr(item, 'matches_criteria'):
                return item.matches_criteria(criteria)
            return False

        result = self.filter(matches_criteria)
        return ModelSearchableCollection[T](
            collection_id=result.collection_id,
            name=result.name,
            description=result.description,
            items=result.items,
            max_size=result.max_size,
            allow_duplicates=result.allow_duplicates,
            tags=result.tags,
            metadata=result.metadata
        )

    def search_by_field(self, field: str, value: Any) -> "ModelSearchableCollection[T]":
        """
        Search for items by a specific field value.

        Args:
            field: Field name to search
            value: Value to match

        Returns:
            New collection with matching items
        """
        return self.search({field: value})

    def get_search_fields(self) -> set[str]:
        """
        Get all available search fields from items.

        Returns:
            Set of field names that can be searched
        """
        fields: set[str] = set()
        for item in self.items:
            if hasattr(item, 'get_search_fields'):
                item_fields = item.get_search_fields()
                if isinstance(item_fields, dict):
                    fields.update(item_fields.keys())
        return fields


# Factory functions for common collection types
def create_collection(items: list[Any] | None = None, **kwargs: Any) -> ModelGenericCollection[Any]:
    """Create a generic collection."""
    return ModelGenericCollection[Any](items=items or [], **kwargs)


def create_identifiable_collection(
    items: list[Any] | None = None, **kwargs: Any
) -> ModelIdentifiableCollection[Any]:
    """Create a collection for identifiable items."""
    return ModelIdentifiableCollection[Any](items=items or [], **kwargs)


def create_searchable_collection(items: list[Any] | None = None, **kwargs: Any) -> ModelSearchableCollection[Any]:
    """Create a searchable collection."""
    return ModelSearchableCollection[Any](items=items or [], **kwargs)


# Export for use
__all__ = [
    "ModelGenericCollection",
    "ModelIdentifiableCollection",
    "ModelSearchableCollection",
    "Identifiable",
    "SearchableItem",
    "create_collection",
    "create_identifiable_collection",
    "create_searchable_collection",
]