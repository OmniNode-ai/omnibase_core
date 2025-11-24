"""
Unit tests for ModelGenericCollection - Generic collection management pattern.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field

from omnibase_core.models.core import ModelGenericCollection
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


class MockItem(BaseModel):
    """Mock item for testing generic collection."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    enabled: bool = True
    is_valid: bool = True
    valid: bool = True
    priority: int = 0
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MockSimpleItem(BaseModel):
    """Simple mock item without optional fields."""

    name: str


class TestModelGenericCollection:
    """Test suite for ModelGenericCollection."""

    def test_create_empty_collection(self):
        """Test creating an empty collection."""
        collection = ModelGenericCollection[MockItem]()

        assert collection.item_count() == 0
        assert collection.items == []
        assert collection.collection_display_name == ""
        assert isinstance(collection.collection_id, UUID)
        assert isinstance(collection.created_at, datetime)

    def test_create_named_collection(self):
        """Test creating a named collection."""
        collection = ModelGenericCollection[MockItem](
            collection_display_name="test_collection",
        )

        assert collection.collection_display_name == "test_collection"
        assert isinstance(collection.collection_id, UUID)

    def test_add_item(self):
        """Test adding items to collection."""
        collection = ModelGenericCollection[MockItem]()
        item = MockItem(name="test_item")

        collection.add_item(item)

        assert collection.item_count() == 1
        assert collection.items[0] == item
        assert collection.updated_at >= collection.created_at

    def test_remove_item_by_id(self):
        """Test removing items by ID."""
        collection = ModelGenericCollection[MockItem]()
        item1 = MockItem(name="item1")
        item2 = MockItem(name="item2")

        collection.add_item(item1)
        collection.add_item(item2)

        # Remove first item
        removed = collection.remove_item(item1.id)

        assert removed is True
        assert collection.item_count() == 1
        assert collection.items[0] == item2

        # Try to remove non-existent item
        fake_id = uuid4()
        removed = collection.remove_item(fake_id)
        assert removed is False

    def test_remove_item_by_index(self):
        """Test removing items by index."""
        collection = ModelGenericCollection[MockItem]()
        items = [MockItem(name=f"item{i}") for i in range(3)]
        collection.extend_items(items)

        # Remove middle item
        removed = collection.remove_item_by_index(1)

        assert removed is True
        assert collection.item_count() == 2
        assert collection.items[0].name == "item0"
        assert collection.items[1].name == "item2"

        # Try to remove out-of-bounds index
        removed = collection.remove_item_by_index(10)
        assert removed is False

    def test_get_item_by_id(self):
        """Test getting items by ID."""
        collection = ModelGenericCollection[MockItem]()
        item = MockItem(name="test_item")
        collection.add_item(item)

        found_item = collection.get_item(item.id)
        assert found_item == item

        # Test non-existent ID
        fake_id = uuid4()
        not_found = collection.get_item(fake_id)
        assert not_found is None

    def test_get_item_by_name(self):
        """Test getting items by name."""
        collection = ModelGenericCollection[MockItem]()
        item = MockItem(name="unique_name")
        collection.add_item(item)

        found_item = collection.get_item_by_name("unique_name")
        assert found_item == item

        # Test non-existent name
        not_found = collection.get_item_by_name("nonexistent")
        assert not_found is None

    def test_get_item_by_index(self):
        """Test getting items by index."""
        collection = ModelGenericCollection[MockItem]()
        items = [MockItem(name=f"item{i}") for i in range(3)]
        collection.extend_items(items)

        # Test valid indices
        assert collection.get_item_by_index(0) == items[0]
        assert collection.get_item_by_index(2) == items[2]

        # Test invalid indices
        assert collection.get_item_by_index(-1) is None
        assert collection.get_item_by_index(10) is None

    def test_filter_items(self):
        """Test filtering items with custom predicate."""
        collection = ModelGenericCollection[MockItem]()
        items = [
            MockItem(name="enabled1", enabled=True),
            MockItem(name="disabled", enabled=False),
            MockItem(name="enabled2", enabled=True),
        ]
        collection.extend_items(items)

        enabled_items = collection.filter_items(lambda item: item.enabled)
        assert len(enabled_items) == 2
        assert enabled_items[0].name == "enabled1"
        assert enabled_items[1].name == "enabled2"

    def test_get_enabled_items(self):
        """Test getting enabled items."""
        collection = ModelGenericCollection[MockItem]()
        items = [
            MockItem(name="enabled", enabled=True),
            MockItem(name="disabled", enabled=False),
        ]
        collection.extend_items(items)

        enabled_items = collection.get_enabled_items()
        assert len(enabled_items) == 1
        assert enabled_items[0].name == "enabled"

    def test_get_enabled_items_without_enabled_field(self):
        """Test that items without 'enabled' field are considered enabled."""
        collection = ModelGenericCollection[MockSimpleItem]()
        item = MockSimpleItem(name="simple")
        collection.add_item(item)

        enabled_items = collection.get_enabled_items()
        assert len(enabled_items) == 1
        assert enabled_items[0] == item

    def test_get_valid_items(self):
        """Test getting valid items."""
        collection = ModelGenericCollection[MockItem]()
        items = [
            MockItem(name="valid", is_valid=True, valid=True),
            MockItem(name="invalid1", is_valid=False, valid=True),
            MockItem(name="invalid2", is_valid=True, valid=False),
            MockItem(name="invalid3", is_valid=False, valid=False),
        ]
        collection.extend_items(items)

        valid_items = collection.get_valid_items()
        assert len(valid_items) == 1
        assert valid_items[0].name == "valid"

    def test_get_items_by_tag(self):
        """Test getting items by tag."""
        collection = ModelGenericCollection[MockItem]()
        items = [
            MockItem(name="item1", tags=["tag1", "tag2"]),
            MockItem(name="item2", tags=["tag2", "tag3"]),
            MockItem(name="item3", tags=["tag3"]),
        ]
        collection.extend_items(items)

        tag2_items = collection.get_items_by_tag("tag2")
        assert len(tag2_items) == 2
        assert tag2_items[0].name == "item1"
        assert tag2_items[1].name == "item2"

    def test_counting_methods(self):
        """Test various counting methods."""
        collection = ModelGenericCollection[MockItem]()
        items = [
            MockItem(name="enabled_valid", enabled=True, is_valid=True),
            MockItem(name="disabled_valid", enabled=False, is_valid=True),
            MockItem(name="enabled_invalid", enabled=True, is_valid=False),
        ]
        collection.extend_items(items)

        assert collection.item_count() == 3
        assert collection.enabled_item_count() == 2
        assert collection.valid_item_count() == 2

    def test_clear_all(self):
        """Test clearing all items."""
        collection = ModelGenericCollection[MockItem]()
        items = [MockItem(name=f"item{i}") for i in range(3)]
        collection.extend_items(items)

        assert collection.item_count() == 3

        collection.clear_all()

        assert collection.item_count() == 0
        assert collection.items == []

    def test_sort_by_priority(self):
        """Test sorting by priority."""
        collection = ModelGenericCollection[MockItem]()
        items = [
            MockItem(name="low", priority=1),
            MockItem(name="high", priority=10),
            MockItem(name="medium", priority=5),
        ]
        collection.extend_items(items)

        # Sort ascending (default)
        collection.sort_by_priority()
        assert collection.items[0].name == "low"
        assert collection.items[2].name == "high"

        # Sort descending
        collection.sort_by_priority(reverse=True)
        assert collection.items[0].name == "high"
        assert collection.items[2].name == "low"

    def test_sort_by_name(self):
        """Test sorting by name."""
        collection = ModelGenericCollection[MockItem]()
        items = [
            MockItem(name="Charlie"),
            MockItem(name="Alice"),
            MockItem(name="Bob"),
        ]
        collection.extend_items(items)

        collection.sort_by_name()
        assert collection.items[0].name == "Alice"
        assert collection.items[1].name == "Bob"
        assert collection.items[2].name == "Charlie"

    def test_sort_by_created_at(self):
        """Test sorting by creation time."""
        collection = ModelGenericCollection[MockItem]()

        # Create items with different timestamps
        from datetime import timedelta

        base_time = datetime.now(UTC)
        items = [
            MockItem(name="newest", created_at=base_time + timedelta(hours=2)),
            MockItem(name="oldest", created_at=base_time),
            MockItem(name="middle", created_at=base_time + timedelta(hours=1)),
        ]
        collection.extend_items(items)

        # Sort ascending (oldest first)
        collection.sort_by_created_at()
        assert collection.items[0].name == "oldest"
        assert collection.items[2].name == "newest"

        # Sort descending (newest first)
        collection.sort_by_created_at(reverse=True)
        assert collection.items[0].name == "newest"
        assert collection.items[2].name == "oldest"

    def test_get_item_names(self):
        """Test getting list of item names."""
        collection = ModelGenericCollection[MockItem]()
        items = [
            MockItem(name="Alice"),
            MockItem(name="Bob"),
            MockItem(name="Charlie"),
        ]
        collection.extend_items(items)

        names = collection.get_item_names()
        assert names == ["Alice", "Bob", "Charlie"]

    def test_has_item_methods(self):
        """Test item existence checking methods."""
        collection = ModelGenericCollection[MockItem]()
        item = MockItem(name="test_item")
        collection.add_item(item)

        assert collection.has_item_with_name("test_item") is True
        assert collection.has_item_with_name("nonexistent") is False
        assert collection.has_item_with_id(item.id) is True
        assert collection.has_item_with_id(uuid4()) is False

    def test_get_summary(self):
        """Test getting collection summary."""
        collection = ModelGenericCollection[MockItem](
            collection_display_name="test_collection",
        )
        items = [
            MockItem(name="enabled_valid", enabled=True, is_valid=True),
            MockItem(name="disabled_invalid", enabled=False, is_valid=False),
        ]
        collection.extend_items(items)

        summary = collection.get_summary()

        assert summary.collection_display_name == "test_collection"
        assert summary.collection_id == collection.collection_id
        assert summary.total_items == 2
        assert summary.enabled_items == 1
        assert summary.valid_items == 1
        assert summary.has_items is True
        assert isinstance(summary.created_at, datetime)
        assert isinstance(summary.updated_at, datetime)

    def test_extend_items(self):
        """Test adding multiple items at once."""
        collection = ModelGenericCollection[MockItem]()
        items = [MockItem(name=f"item{i}") for i in range(3)]

        collection.extend_items(items)

        assert collection.item_count() == 3
        for i, item in enumerate(items):
            assert collection.items[i] == item

    def test_find_items(self):
        """Test finding items by attribute values."""
        collection = ModelGenericCollection[MockItem]()
        items = [
            MockItem(name="item1", enabled=True, priority=5),
            MockItem(name="item2", enabled=False, priority=5),
            MockItem(name="item3", enabled=True, priority=10),
        ]
        collection.extend_items(items)

        # Find by single attribute
        enabled_items = collection.find_items(enabled=True)
        assert len(enabled_items) == 2

        # Find by multiple attributes
        enabled_priority5_items = collection.find_items(enabled=True, priority=5)
        assert len(enabled_priority5_items) == 1
        assert enabled_priority5_items[0].name == "item1"

        # Find with no matches
        no_matches = collection.find_items(enabled=True, priority=999)
        assert len(no_matches) == 0

    def test_update_item(self):
        """Test updating item attributes."""
        collection = ModelGenericCollection[MockItem]()
        item = MockItem(name="test_item", enabled=True, priority=5)
        collection.add_item(item)

        # Update existing item
        updated = collection.update_item(item.id, enabled=False, priority=10)
        assert updated is True
        assert item.enabled is False
        assert item.priority == 10

        # Try to update non-existent item
        fake_id = uuid4()
        not_updated = collection.update_item(fake_id, enabled=True)
        assert not_updated is False

    def test_class_methods(self):
        """Test class methods for creating collections."""
        # Test create_empty
        empty_collection = ModelGenericCollection.create_empty("empty_test")
        assert empty_collection.collection_display_name == "empty_test"
        assert empty_collection.item_count() == 0
        assert isinstance(empty_collection.collection_id, UUID)

        # Test create_from_items
        items = [MockItem(name=f"item{i}") for i in range(3)]
        collection = ModelGenericCollection.create_from_items(items, "test_collection")
        assert collection.collection_display_name == "test_collection"
        assert collection.item_count() == 3
        assert isinstance(collection.collection_id, UUID)

    def test_timestamp_updates(self):
        """Test that timestamps are updated on modifications."""
        collection = ModelGenericCollection[MockItem]()
        initial_updated_at = collection.updated_at

        # Add item should update timestamp
        item = MockItem(name="test")
        collection.add_item(item)
        assert collection.updated_at > initial_updated_at

        # Remove item should update timestamp
        updated_at_after_add = collection.updated_at
        collection.remove_item(item.id)
        assert collection.updated_at > updated_at_after_add

        # Sorting should update timestamp
        items = [MockItem(name=f"item{i}", priority=i) for i in range(3)]
        collection.extend_items(items)
        updated_at_after_extend = collection.updated_at
        collection.sort_by_priority()
        assert collection.updated_at > updated_at_after_extend

    def test_collection_display_name_access(self):
        """Test collection_display_name property access."""
        # Test property access
        collection = ModelGenericCollection[MockItem](
            collection_display_name="test_collection",
        )

        # Property getter should work
        assert collection.collection_display_name == "test_collection"

        # Property setter should work
        collection.collection_display_name = "updated_name"
        assert collection.collection_display_name == "updated_name"

        # Test class factory methods
        empty_collection = ModelGenericCollection.create_empty_with_name("legacy_empty")
        assert empty_collection.collection_display_name == "legacy_empty"
        assert empty_collection.collection_display_name == "legacy_empty"

        items = [MockItem(name=f"item{i}") for i in range(2)]
        legacy_collection = ModelGenericCollection.create_from_items_with_name(
            items,
            "legacy_collection",
        )
        assert legacy_collection.collection_display_name == "legacy_collection"
        assert legacy_collection.collection_display_name == "legacy_collection"
        assert legacy_collection.item_count() == 2

        # Test summary access
        summary = legacy_collection.get_summary()
        assert summary.collection_display_name == "legacy_collection"
        assert summary.collection_display_name == "legacy_collection"

        # Test summary setter
        summary.collection_display_name = "updated_summary"
        assert summary.collection_display_name == "updated_summary"
        assert summary.collection_display_name == "updated_summary"

    def test_collection_id_uniqueness(self):
        """Test that collection IDs are unique."""
        collection1 = ModelGenericCollection[MockItem]()
        collection2 = ModelGenericCollection[MockItem]()

        # IDs should be different
        assert collection1.collection_id != collection2.collection_id

        # But we can specify the same ID if needed
        shared_id = uuid4()
        collection3 = ModelGenericCollection.create_empty(collection_id=shared_id)
        collection4 = ModelGenericCollection.create_from_items(
            [],
            collection_id=shared_id,
        )

        assert collection3.collection_id == shared_id
        assert collection4.collection_id == shared_id
        assert collection3.collection_id == collection4.collection_id


class TestModelGenericCollectionEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_collection_operations(self):
        """Test operations on empty collections."""
        collection = ModelGenericCollection[MockItem]()

        assert collection.get_item_by_name("nonexistent") is None
        assert collection.get_item_by_index(0) is None
        assert collection.get_enabled_items() == []
        assert collection.get_valid_items() == []
        assert collection.filter_items(lambda x: True) == []
        assert collection.get_item_names() == []

    def test_items_without_optional_attributes(self):
        """Test operations on items that don't have optional attributes."""
        collection = ModelGenericCollection[MockSimpleItem]()
        item = MockSimpleItem(name="simple")
        collection.add_item(item)

        # These should not raise errors even though item doesn't have these attributes
        enabled_items = collection.get_enabled_items()
        assert len(enabled_items) == 1

        valid_items = collection.get_valid_items()
        assert len(valid_items) == 1

        # Sorting by non-existent fields should use defaults
        collection.sort_by_priority()  # Should not error
        assert collection.item_count() == 1

    def test_duplicate_names(self):
        """Test behavior with duplicate names."""
        collection = ModelGenericCollection[MockItem]()
        item1 = MockItem(name="duplicate")
        item2 = MockItem(name="duplicate")
        collection.add_item(item1)
        collection.add_item(item2)

        # get_item_by_name should return first match
        found = collection.get_item_by_name("duplicate")
        assert found == item1

        # Both items should exist in collection
        assert collection.item_count() == 2


if __name__ == "__main__":
    pytest.main([__file__])
