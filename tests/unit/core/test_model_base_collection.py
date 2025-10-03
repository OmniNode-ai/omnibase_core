"""
Tests for ModelBaseCollection abstract base class.

Validates that ModelBaseCollection works correctly with concrete implementations
and enforces the collection protocol.
"""

from collections.abc import Iterator

import pytest
from pydantic import Field

from omnibase_core.models.base.model_collection import ModelBaseCollection


class ConcreteCollection(ModelBaseCollection[str]):
    """Concrete implementation of ModelBaseCollection for testing."""

    items: list[str] = Field(default_factory=list)

    def add_item(self, item: str) -> None:
        """Add an item to the collection."""
        self.items.append(item)

    def remove_item(self, item: str) -> bool:
        """Remove an item from the collection."""
        if item in self.items:
            self.items.remove(item)
            return True
        return False

    def get_item_count(self) -> int:
        """Get the number of items in the collection."""
        return len(self.items)

    def iter_items(self) -> Iterator[str]:
        """Iterate over items in the collection."""
        return iter(self.items)

    def get_items(self) -> list[str]:
        """Get all items as a list."""
        return self.items.copy()


class IntegerCollection(ModelBaseCollection[int]):
    """Concrete integer collection for testing."""

    values: list[int] = Field(default_factory=list)

    def add_item(self, item: int) -> None:
        """Add an integer to the collection."""
        self.values.append(item)

    def remove_item(self, item: int) -> bool:
        """Remove an integer from the collection."""
        try:
            self.values.remove(item)
            return True
        except ValueError:
            return False

    def get_item_count(self) -> int:
        """Get the number of integers."""
        return len(self.values)

    def iter_items(self) -> Iterator[int]:
        """Iterate over integers."""
        return iter(self.values)

    def get_items(self) -> list[int]:
        """Get all integers as a list."""
        return self.values[:]


class TestModelBaseCollectionAbstract:
    """Test that ModelBaseCollection enforces abstract methods."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that ModelBaseCollection cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            ModelBaseCollection()  # type: ignore[abstract]

    def test_missing_add_item_method(self):
        """Test that implementations must define add_item."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):

            class IncompleteCollection(ModelBaseCollection[str]):
                def remove_item(self, item: str) -> bool:
                    return True

                def get_item_count(self) -> int:
                    return 0

                def iter_items(self) -> Iterator[str]:
                    return iter([])

                def get_items(self) -> list[str]:
                    return []

            IncompleteCollection()  # type: ignore[abstract]

    def test_missing_remove_item_method(self):
        """Test that implementations must define remove_item."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):

            class IncompleteCollection(ModelBaseCollection[str]):
                def add_item(self, item: str) -> None:
                    pass

                def get_item_count(self) -> int:
                    return 0

                def iter_items(self) -> Iterator[str]:
                    return iter([])

                def get_items(self) -> list[str]:
                    return []

            IncompleteCollection()  # type: ignore[abstract]


class TestConcreteCollectionImplementation:
    """Test concrete collection implementations."""

    def test_create_empty_collection(self):
        """Test creating an empty collection."""
        collection = ConcreteCollection()
        assert collection.get_item_count() == 0
        assert collection.get_items() == []

    def test_add_single_item(self):
        """Test adding a single item."""
        collection = ConcreteCollection()
        collection.add_item("test")
        assert collection.get_item_count() == 1
        assert "test" in collection.get_items()

    def test_add_multiple_items(self):
        """Test adding multiple items."""
        collection = ConcreteCollection()
        collection.add_item("first")
        collection.add_item("second")
        collection.add_item("third")
        assert collection.get_item_count() == 3
        assert collection.get_items() == ["first", "second", "third"]

    def test_remove_existing_item(self):
        """Test removing an existing item."""
        collection = ConcreteCollection(items=["a", "b", "c"])
        result = collection.remove_item("b")
        assert result is True
        assert collection.get_item_count() == 2
        assert "b" not in collection.get_items()

    def test_remove_nonexistent_item(self):
        """Test removing an item that doesn't exist."""
        collection = ConcreteCollection(items=["a", "b", "c"])
        result = collection.remove_item("d")
        assert result is False
        assert collection.get_item_count() == 3

    def test_iter_items(self):
        """Test iterating over items."""
        collection = ConcreteCollection(items=["x", "y", "z"])
        items = list(collection.iter_items())
        assert items == ["x", "y", "z"]

    def test_get_items_returns_copy(self):
        """Test that get_items returns a copy, not the original list."""
        collection = ConcreteCollection(items=["a", "b"])
        items = collection.get_items()
        items.append("c")
        # Original collection should not be modified
        assert collection.get_item_count() == 2
        assert "c" not in collection.get_items()

    def test_pydantic_validation(self):
        """Test that Pydantic validation works."""
        collection = ConcreteCollection(items=["test"])
        # Test validation on assignment (enabled in model_config)
        collection.items = ["new", "values"]
        assert collection.get_items() == ["new", "values"]

    def test_model_config_extra_ignore(self):
        """Test that extra fields are ignored."""
        collection = ConcreteCollection(items=["test"], unknown_field="ignored")  # type: ignore[call-arg]
        assert collection.get_item_count() == 1
        assert not hasattr(collection, "unknown_field")


class TestIntegerCollectionImplementation:
    """Test integer collection implementation."""

    def test_integer_collection_operations(self):
        """Test operations with integer type."""
        collection = IntegerCollection()
        collection.add_item(10)
        collection.add_item(20)
        collection.add_item(30)

        assert collection.get_item_count() == 3
        assert 20 in collection.get_items()
        assert collection.remove_item(20) is True
        assert collection.get_item_count() == 2
        assert 20 not in collection.get_items()

    def test_integer_collection_iteration(self):
        """Test iterating over integers."""
        collection = IntegerCollection(values=[1, 2, 3, 4, 5])
        total = sum(collection.iter_items())
        assert total == 15

    def test_remove_first_occurrence(self):
        """Test that remove only removes first occurrence."""
        collection = IntegerCollection(values=[1, 2, 3, 2, 4])
        collection.remove_item(2)
        # Should have one 2 remaining
        assert collection.get_items() == [1, 3, 2, 4]


class TestCollectionModelSerialization:
    """Test collection serialization and deserialization."""

    def test_serialize_collection(self):
        """Test serializing a collection to dict."""
        collection = ConcreteCollection(items=["a", "b", "c"])
        data = collection.model_dump()
        assert data == {"items": ["a", "b", "c"]}

    def test_deserialize_collection(self):
        """Test deserializing a collection from dict."""
        data = {"items": ["x", "y", "z"]}
        collection = ConcreteCollection(**data)
        assert collection.get_items() == ["x", "y", "z"]

    def test_json_serialization(self):
        """Test JSON serialization."""
        collection = ConcreteCollection(items=["test1", "test2"])
        json_str = collection.model_dump_json()
        assert '"items"' in json_str
        assert '"test1"' in json_str

    def test_json_deserialization(self):
        """Test JSON deserialization."""
        json_str = '{"items": ["a", "b"]}'
        collection = ConcreteCollection.model_validate_json(json_str)
        assert collection.get_items() == ["a", "b"]


class TestCollectionEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_collection_operations(self):
        """Test operations on empty collection."""
        collection = ConcreteCollection()
        assert collection.get_item_count() == 0
        assert list(collection.iter_items()) == []
        assert collection.remove_item("anything") is False

    def test_add_duplicate_items(self):
        """Test adding duplicate items (allowed)."""
        collection = ConcreteCollection()
        collection.add_item("duplicate")
        collection.add_item("duplicate")
        assert collection.get_item_count() == 2

    def test_add_empty_string(self):
        """Test adding empty string."""
        collection = ConcreteCollection()
        collection.add_item("")
        assert collection.get_item_count() == 1
        assert "" in collection.get_items()

    def test_large_collection(self):
        """Test collection with many items."""
        collection = ConcreteCollection()
        for i in range(1000):
            collection.add_item(f"item_{i}")
        assert collection.get_item_count() == 1000

    def test_collection_copy_constructor(self):
        """Test creating collection from another collection's data."""
        original = ConcreteCollection(items=["a", "b", "c"])
        copy = ConcreteCollection(items=original.get_items())
        assert copy.get_items() == original.get_items()
        # Verify they are independent
        copy.add_item("d")
        assert copy.get_item_count() == 4
        assert original.get_item_count() == 3


class TestCollectionTypeParameter:
    """Test that collection works with different type parameters."""

    def test_string_collection(self):
        """Test collection with string type."""
        collection = ConcreteCollection(items=["str1", "str2"])
        assert all(isinstance(item, str) for item in collection.iter_items())

    def test_integer_collection_type(self):
        """Test collection with integer type."""
        collection = IntegerCollection(values=[1, 2, 3])
        assert all(isinstance(item, int) for item in collection.iter_items())

    def test_type_hints_preserved(self):
        """Test that type hints are preserved in implementation."""
        from typing import get_type_hints

        hints = get_type_hints(ConcreteCollection.add_item)
        assert "item" in hints
        # The actual type checking is done by mypy/pyright, not at runtime
