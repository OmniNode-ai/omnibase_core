"""
Tests for EnumFileEventType enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_file_event_type import EnumFileEventType


class TestEnumFileEventType:
    """Test cases for EnumFileEventType enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert EnumFileEventType.CREATED.value == "created"
        assert EnumFileEventType.MODIFIED.value == "modified"
        assert EnumFileEventType.DELETED.value == "deleted"
        assert EnumFileEventType.MOVED.value == "moved"
        assert EnumFileEventType.RENAMED.value == "renamed"
        assert EnumFileEventType.PERMISSION_CHANGED.value == "permission_changed"
        assert EnumFileEventType.ATTRIBUTE_CHANGED.value == "attribute_changed"

    def test_enum_inheritance(self):
        """Test that enum inherits from Enum."""
        assert issubclass(EnumFileEventType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        assert str(EnumFileEventType.CREATED) == "EnumFileEventType.CREATED"
        assert str(EnumFileEventType.MODIFIED) == "EnumFileEventType.MODIFIED"
        assert str(EnumFileEventType.DELETED) == "EnumFileEventType.DELETED"
        assert str(EnumFileEventType.MOVED) == "EnumFileEventType.MOVED"
        assert str(EnumFileEventType.RENAMED) == "EnumFileEventType.RENAMED"
        assert (
            str(EnumFileEventType.PERMISSION_CHANGED)
            == "EnumFileEventType.PERMISSION_CHANGED"
        )
        assert (
            str(EnumFileEventType.ATTRIBUTE_CHANGED)
            == "EnumFileEventType.ATTRIBUTE_CHANGED"
        )

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumFileEventType)
        assert len(values) == 7
        assert EnumFileEventType.CREATED in values
        assert EnumFileEventType.MODIFIED in values
        assert EnumFileEventType.DELETED in values
        assert EnumFileEventType.MOVED in values
        assert EnumFileEventType.RENAMED in values
        assert EnumFileEventType.PERMISSION_CHANGED in values
        assert EnumFileEventType.ATTRIBUTE_CHANGED in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert "created" in EnumFileEventType
        assert "modified" in EnumFileEventType
        assert "deleted" in EnumFileEventType
        assert "moved" in EnumFileEventType
        assert "renamed" in EnumFileEventType
        assert "permission_changed" in EnumFileEventType
        assert "attribute_changed" in EnumFileEventType
        assert "invalid" not in EnumFileEventType

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumFileEventType.CREATED.value == "created"
        assert EnumFileEventType.MODIFIED.value == "modified"
        assert EnumFileEventType.DELETED.value == "deleted"
        assert EnumFileEventType.MOVED.value == "moved"
        assert EnumFileEventType.RENAMED.value == "renamed"
        assert EnumFileEventType.PERMISSION_CHANGED.value == "permission_changed"
        assert EnumFileEventType.ATTRIBUTE_CHANGED.value == "attribute_changed"

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert EnumFileEventType.CREATED.value == "created"
        assert EnumFileEventType.MODIFIED.value == "modified"
        assert EnumFileEventType.DELETED.value == "deleted"
        assert EnumFileEventType.MOVED.value == "moved"
        assert EnumFileEventType.RENAMED.value == "renamed"
        assert EnumFileEventType.PERMISSION_CHANGED.value == "permission_changed"
        assert EnumFileEventType.ATTRIBUTE_CHANGED.value == "attribute_changed"

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert EnumFileEventType("created") == EnumFileEventType.CREATED
        assert EnumFileEventType("modified") == EnumFileEventType.MODIFIED
        assert EnumFileEventType("deleted") == EnumFileEventType.DELETED
        assert EnumFileEventType("moved") == EnumFileEventType.MOVED
        assert EnumFileEventType("renamed") == EnumFileEventType.RENAMED
        assert (
            EnumFileEventType("permission_changed")
            == EnumFileEventType.PERMISSION_CHANGED
        )
        assert (
            EnumFileEventType("attribute_changed")
            == EnumFileEventType.ATTRIBUTE_CHANGED
        )

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumFileEventType("invalid")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [event_type.value for event_type in EnumFileEventType]
        expected_values = [
            "created",
            "modified",
            "deleted",
            "moved",
            "renamed",
            "permission_changed",
            "attribute_changed",
        ]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Types of filesystem events that can be monitored"
            in EnumFileEventType.__doc__
        )
