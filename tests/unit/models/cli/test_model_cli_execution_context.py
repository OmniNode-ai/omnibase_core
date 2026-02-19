# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelCliExecutionContext.

Validates CLI execution context model functionality including
validation, serialization, type checking, and protocol implementations.
"""

from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_context_source import EnumContextSource
from omnibase_core.enums.enum_context_type import EnumContextType
from omnibase_core.models.cli.model_cli_execution_context import (
    ModelCliExecutionContext,
)


@pytest.mark.unit
class TestModelCliExecutionContextBasic:
    """Test basic CLI execution context functionality."""

    def test_minimal_context_creation(self):
        """Test creating context with minimal required fields."""
        context = ModelCliExecutionContext(
            key="test_key",
            value="test_value",
            context_type=EnumContextType.SYSTEM,
        )

        assert context.key == "test_key"
        assert context.value == "test_value"
        assert context.context_type == EnumContextType.SYSTEM
        assert context.is_persistent is False
        assert context.priority == 0
        assert isinstance(context.created_at, datetime)
        assert isinstance(context.updated_at, datetime)

    def test_full_context_creation(self):
        """Test creating context with all fields."""
        created = datetime.now()
        updated = datetime.now()

        context = ModelCliExecutionContext(
            key="full_key",
            value="full_value",
            context_type=EnumContextType.USER,
            is_persistent=True,
            priority=5,
            created_at=created,
            updated_at=updated,
            description="Test description",
            source=EnumContextSource.USER,
        )

        assert context.key == "full_key"
        assert context.value == "full_value"
        assert context.context_type == EnumContextType.USER
        assert context.is_persistent is True
        assert context.priority == 5
        assert context.created_at == created
        assert context.updated_at == updated
        assert context.description == "Test description"
        assert context.source == EnumContextSource.USER

    def test_context_with_string_value(self):
        """Test context with string value."""
        context = ModelCliExecutionContext(
            key="string_key",
            value="string_value",
            context_type=EnumContextType.SYSTEM,
        )

        assert isinstance(context.value, str)
        assert context.value == "string_value"

    def test_context_with_integer_value(self):
        """Test context with integer value."""
        context = ModelCliExecutionContext(
            key="int_key",
            value=42,
            context_type=EnumContextType.SYSTEM,
        )

        assert isinstance(context.value, int)
        assert context.value == 42

    def test_context_with_float_value(self):
        """Test context with float value."""
        context = ModelCliExecutionContext(
            key="float_key",
            value=3.14,
            context_type=EnumContextType.SYSTEM,
        )

        assert isinstance(context.value, float)
        assert context.value == 3.14

    def test_context_with_boolean_value(self):
        """Test context with boolean value."""
        context = ModelCliExecutionContext(
            key="bool_key",
            value=True,
            context_type=EnumContextType.SYSTEM,
        )

        assert isinstance(context.value, bool)
        assert context.value is True

    def test_context_with_path_value(self):
        """Test context with Path value."""
        path = Path("/fake/test/path")
        context = ModelCliExecutionContext(
            key="path_key",
            value=path,
            context_type=EnumContextType.SYSTEM,
        )

        assert isinstance(context.value, Path)
        assert context.value == path

    def test_context_with_uuid_value(self):
        """Test context with UUID value."""
        test_uuid = uuid4()
        context = ModelCliExecutionContext(
            key="uuid_key",
            value=test_uuid,
            context_type=EnumContextType.SYSTEM,
        )

        assert isinstance(context.value, UUID)
        assert context.value == test_uuid

    def test_context_with_datetime_value(self):
        """Test context with datetime value."""
        now = datetime.now()
        context = ModelCliExecutionContext(
            key="datetime_key",
            value=now,
            context_type=EnumContextType.SYSTEM,
        )

        assert isinstance(context.value, datetime)
        assert context.value == now

    def test_context_with_list_value(self):
        """Test context with list value."""
        test_list = ["item1", "item2", "item3"]
        context = ModelCliExecutionContext(
            key="list_key",
            value=test_list,
            context_type=EnumContextType.SYSTEM,
        )

        assert isinstance(context.value, list)
        assert context.value == test_list


@pytest.mark.unit
class TestModelCliExecutionContextMethods:
    """Test context instance methods."""

    def test_get_string_value_from_string(self):
        """Test getting string representation from string value."""
        context = ModelCliExecutionContext(
            key="test",
            value="string_value",
            context_type=EnumContextType.SYSTEM,
        )

        result = context.get_string_value()
        assert result == "string_value"

    def test_get_string_value_from_integer(self):
        """Test getting string representation from integer value."""
        context = ModelCliExecutionContext(
            key="test",
            value=42,
            context_type=EnumContextType.SYSTEM,
        )

        result = context.get_string_value()
        assert result == "42"

    def test_get_string_value_from_path(self):
        """Test getting string representation from Path value."""
        path = Path("/fake/test/path")
        context = ModelCliExecutionContext(
            key="test",
            value=path,
            context_type=EnumContextType.SYSTEM,
        )

        result = context.get_string_value()
        assert result == str(path)

    def test_get_string_value_from_datetime(self):
        """Test getting string representation from datetime value."""
        now = datetime.now()
        context = ModelCliExecutionContext(
            key="test",
            value=now,
            context_type=EnumContextType.SYSTEM,
        )

        result = context.get_string_value()
        assert result == now.isoformat()

    def test_get_string_value_from_list(self):
        """Test getting string representation from list value."""
        test_list = ["item1", "item2", "item3"]
        context = ModelCliExecutionContext(
            key="test",
            value=test_list,
            context_type=EnumContextType.SYSTEM,
        )

        result = context.get_string_value()
        assert result == "item1,item2,item3"

    def test_get_typed_value(self):
        """Test getting typed value."""
        test_uuid = uuid4()
        context = ModelCliExecutionContext(
            key="test",
            value=test_uuid,
            context_type=EnumContextType.SYSTEM,
        )

        result = context.get_typed_value()
        assert result == test_uuid
        assert isinstance(result, UUID)

    def test_is_datetime_value_true(self):
        """Test checking if value is datetime when it is."""
        context = ModelCliExecutionContext(
            key="test",
            value=datetime.now(),
            context_type=EnumContextType.SYSTEM,
        )

        assert context.is_datetime_value() is True

    def test_is_datetime_value_false(self):
        """Test checking if value is datetime when it is not."""
        context = ModelCliExecutionContext(
            key="test",
            value="not a datetime",
            context_type=EnumContextType.SYSTEM,
        )

        assert context.is_datetime_value() is False

    def test_is_path_value_true(self):
        """Test checking if value is Path when it is."""
        context = ModelCliExecutionContext(
            key="test",
            value=Path("/fake/test/path"),
            context_type=EnumContextType.SYSTEM,
        )

        assert context.is_path_value() is True

    def test_is_path_value_false(self):
        """Test checking if value is Path when it is not."""
        context = ModelCliExecutionContext(
            key="test",
            value="not a path",
            context_type=EnumContextType.SYSTEM,
        )

        assert context.is_path_value() is False

    def test_is_uuid_value_true(self):
        """Test checking if value is UUID when it is."""
        context = ModelCliExecutionContext(
            key="test",
            value=uuid4(),
            context_type=EnumContextType.SYSTEM,
        )

        assert context.is_uuid_value() is True

    def test_is_uuid_value_false(self):
        """Test checking if value is UUID when it is not."""
        context = ModelCliExecutionContext(
            key="test",
            value="not a uuid",
            context_type=EnumContextType.SYSTEM,
        )

        assert context.is_uuid_value() is False

    def test_update_value(self):
        """Test updating context value."""
        context = ModelCliExecutionContext(
            key="test",
            value="original",
            context_type=EnumContextType.SYSTEM,
        )

        original_updated_at = context.updated_at

        # Update value
        context.update_value("new_value")

        assert context.value == "new_value"
        assert context.updated_at > original_updated_at


@pytest.mark.unit
class TestModelCliExecutionContextValidation:
    """Test context validation."""

    def test_priority_minimum_boundary(self):
        """Test priority minimum boundary (0)."""
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
            priority=0,
        )

        assert context.priority == 0

    def test_priority_maximum_boundary(self):
        """Test priority maximum boundary (10)."""
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
            priority=10,
        )

        assert context.priority == 10

    def test_priority_below_minimum_raises_error(self):
        """Test that priority below minimum raises validation error."""
        with pytest.raises(Exception):  # Pydantic validation error
            ModelCliExecutionContext(
                key="test",
                value="value",
                context_type=EnumContextType.SYSTEM,
                priority=-1,
            )

    def test_priority_above_maximum_raises_error(self):
        """Test that priority above maximum raises validation error."""
        with pytest.raises(Exception):  # Pydantic validation error
            ModelCliExecutionContext(
                key="test",
                value="value",
                context_type=EnumContextType.SYSTEM,
                priority=11,
            )


@pytest.mark.unit
class TestModelCliExecutionContextProtocols:
    """Test protocol method implementations."""

    def test_serialize(self):
        """Test serialize method (Serializable protocol)."""
        context = ModelCliExecutionContext(
            key="test",
            value="test_value",
            context_type=EnumContextType.SYSTEM,
            priority=5,
        )

        data = context.serialize()

        assert isinstance(data, dict)
        assert data["key"] == "test"
        assert data["priority"] == 5
        assert "context_type" in data

    def test_get_name(self):
        """Test get_name method (Nameable protocol)."""
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
        )

        name = context.get_name()

        assert "ModelCliExecutionContext" in name

    def test_set_name(self):
        """Test set_name method (Nameable protocol)."""
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
        )

        # Should not raise exception even if no name field
        context.set_name("test_name")

    def test_validate_instance(self):
        """Test validate_instance method (ProtocolValidatable protocol)."""
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
        )

        result = context.validate_instance()

        assert result is True


@pytest.mark.unit
class TestModelCliExecutionContextSerialization:
    """Test serialization and deserialization."""

    def test_model_dump(self):
        """Test serialization to dictionary."""
        context = ModelCliExecutionContext(
            key="test",
            value="test_value",
            context_type=EnumContextType.SYSTEM,
            priority=5,
        )

        data = context.model_dump()

        assert data["key"] == "test"
        assert data["value"] == "test_value"
        assert data["priority"] == 5

    def test_round_trip_serialization_with_string(self):
        """Test serialization and deserialization with string value."""
        original = ModelCliExecutionContext(
            key="test",
            value="string_value",
            context_type=EnumContextType.USER,
            is_persistent=True,
            priority=7,
        )

        # Serialize
        data = original.model_dump()

        # Deserialize
        restored = ModelCliExecutionContext.model_validate(data)

        assert restored.key == original.key
        assert restored.value == original.value
        assert restored.context_type == original.context_type
        assert restored.is_persistent == original.is_persistent
        assert restored.priority == original.priority

    def test_round_trip_serialization_with_integer(self):
        """Test serialization and deserialization with integer value."""
        original = ModelCliExecutionContext(
            key="test",
            value=42,
            context_type=EnumContextType.SYSTEM,
        )

        # Serialize
        data = original.model_dump()

        # Deserialize
        restored = ModelCliExecutionContext.model_validate(data)

        assert restored.value == original.value
        assert isinstance(restored.value, int)


@pytest.mark.unit
class TestModelCliExecutionContextEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_description(self):
        """Test with empty description."""
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
            description="",
        )

        assert context.description == ""

    def test_long_description(self):
        """Test with very long description."""
        long_desc = "x" * 1000
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
            description=long_desc,
        )

        assert len(context.description) == 1000

    def test_empty_key(self):
        """Test with empty key (should still work)."""
        context = ModelCliExecutionContext(
            key="",
            value="value",
            context_type=EnumContextType.SYSTEM,
        )

        assert context.key == ""

    def test_none_value_is_valid(self):
        """Test that None value is valid."""
        context = ModelCliExecutionContext(
            key="test",
            value=None,
            context_type=EnumContextType.SYSTEM,
        )

        assert context.value is None

    def test_complex_nested_list_value(self):
        """Test with complex nested list value."""
        complex_value = [["nested", "list"], [1, 2, 3], {"dict": "in list"}]
        context = ModelCliExecutionContext(
            key="test",
            value=complex_value,
            context_type=EnumContextType.SYSTEM,
        )

        assert context.value == complex_value

    def test_dict_value(self):
        """Test with dictionary value."""
        dict_value = {"key1": "value1", "key2": 42}
        context = ModelCliExecutionContext(
            key="test",
            value=dict_value,
            context_type=EnumContextType.SYSTEM,
        )

        assert context.value == dict_value

    def test_all_context_types(self):
        """Test creating context with all context types."""
        for context_type in EnumContextType:
            context = ModelCliExecutionContext(
                key="test",
                value="value",
                context_type=context_type,
            )
            assert context.context_type == context_type

    def test_all_context_sources(self):
        """Test creating context with all context sources."""
        for source in EnumContextSource:
            context = ModelCliExecutionContext(
                key="test",
                value="value",
                context_type=EnumContextType.SYSTEM,
                source=source,
            )
            assert context.source == source

    def test_priority_middle_values(self):
        """Test various priority values in the valid range."""
        for priority in [0, 3, 5, 7, 10]:
            context = ModelCliExecutionContext(
                key="test",
                value="value",
                context_type=EnumContextType.SYSTEM,
                priority=priority,
            )
            assert context.priority == priority

    def test_update_value_multiple_times(self):
        """Test updating value multiple times."""
        context = ModelCliExecutionContext(
            key="test",
            value="original",
            context_type=EnumContextType.SYSTEM,
        )

        context.update_value("update1")
        assert context.value == "update1"

        context.update_value("update2")
        assert context.value == "update2"

        context.update_value(42)
        assert context.value == 42


@pytest.mark.unit
class TestModelCliExecutionContextTypeHandling:
    """Test type handling and conversions."""

    def test_get_string_value_from_boolean(self):
        """Test getting string from boolean value."""
        context = ModelCliExecutionContext(
            key="test",
            value=True,
            context_type=EnumContextType.SYSTEM,
        )

        result = context.get_string_value()
        assert result == "True"

    def test_get_string_value_from_float(self):
        """Test getting string from float value."""
        context = ModelCliExecutionContext(
            key="test",
            value=3.14159,
            context_type=EnumContextType.SYSTEM,
        )

        result = context.get_string_value()
        assert "3.14" in result

    def test_get_string_value_from_uuid(self):
        """Test getting string from UUID value."""
        test_uuid = uuid4()
        context = ModelCliExecutionContext(
            key="test",
            value=test_uuid,
            context_type=EnumContextType.SYSTEM,
        )

        result = context.get_string_value()
        assert result == str(test_uuid)

    def test_get_string_value_from_empty_list(self):
        """Test getting string from empty list."""
        context = ModelCliExecutionContext(
            key="test",
            value=[],
            context_type=EnumContextType.SYSTEM,
        )

        result = context.get_string_value()
        assert result == ""

    def test_get_string_value_from_single_item_list(self):
        """Test getting string from single item list."""
        context = ModelCliExecutionContext(
            key="test",
            value=["single_item"],
            context_type=EnumContextType.SYSTEM,
        )

        result = context.get_string_value()
        assert result == "single_item"
