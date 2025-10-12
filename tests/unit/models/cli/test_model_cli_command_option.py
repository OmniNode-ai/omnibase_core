"""
Comprehensive tests for ModelCliCommandOption.

Tests discriminated union typing, value type validation, factory methods,
and proper handling of CLI command options with type safety.
"""

import uuid
from uuid import UUID

import pytest

from omnibase_core.enums.enum_cli_option_value_type import EnumCliOptionValueType
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.cli.model_cli_command_option import ModelCliCommandOption


class TestModelCliCommandOptionBasic:
    """Test basic option creation and configuration."""

    def test_create_string_option_direct(self) -> None:
        """Test creating string option directly."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption(
            option_id=option_id,
            option_display_name="--verbose",
            value="debug",
            value_type=EnumCliOptionValueType.STRING,
        )

        assert option.option_id == option_id
        assert option.option_display_name == "--verbose"
        assert option.value == "debug"
        assert option.value_type == EnumCliOptionValueType.STRING
        assert not option.is_flag
        assert not option.is_required
        assert not option.is_multiple

    def test_create_integer_option_direct(self) -> None:
        """Test creating integer option directly."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption(
            option_id=option_id,
            option_display_name="--count",
            value=42,
            value_type=EnumCliOptionValueType.INTEGER,
        )

        assert option.option_id == option_id
        assert option.value == 42
        assert option.value_type == EnumCliOptionValueType.INTEGER

    def test_create_boolean_option_direct(self) -> None:
        """Test creating boolean option directly."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption(
            option_id=option_id,
            option_display_name="--debug",
            value=True,
            value_type=EnumCliOptionValueType.BOOLEAN,
            is_flag=True,
        )

        assert option.value is True
        assert option.value_type == EnumCliOptionValueType.BOOLEAN
        assert option.is_flag is True

    def test_create_float_option_direct(self) -> None:
        """Test creating float option directly."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption(
            option_id=option_id,
            option_display_name="--threshold",
            value=3.14,
            value_type=EnumCliOptionValueType.FLOAT,
        )

        assert option.value == 3.14
        assert option.value_type == EnumCliOptionValueType.FLOAT

    def test_create_uuid_option_direct(self) -> None:
        """Test creating UUID option directly."""
        option_id = uuid.uuid4()
        value_uuid = uuid.uuid4()
        option = ModelCliCommandOption(
            option_id=option_id,
            option_display_name="--entity-id",
            value=value_uuid,
            value_type=EnumCliOptionValueType.UUID,
        )

        assert option.value == value_uuid
        assert option.value_type == EnumCliOptionValueType.UUID

    def test_create_string_list_option_direct(self) -> None:
        """Test creating string list option directly."""
        option_id = uuid.uuid4()
        value_list = ["tag1", "tag2", "tag3"]
        option = ModelCliCommandOption(
            option_id=option_id,
            option_display_name="--tags",
            value=value_list,
            value_type=EnumCliOptionValueType.STRING_LIST,
            is_multiple=True,
        )

        assert option.value == value_list
        assert option.value_type == EnumCliOptionValueType.STRING_LIST
        assert option.is_multiple is True


class TestModelCliCommandOptionFactoryMethods:
    """Test factory methods for creating typed options."""

    def test_from_string(self) -> None:
        """Test creating option from string factory method."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_string(
            option_id=option_id,
            value="test_value",
            option_display_name="--name",
            description="Name option",
        )

        assert option.option_id == option_id
        assert option.value == "test_value"
        assert option.value_type == EnumCliOptionValueType.STRING
        assert option.option_display_name == "--name"
        assert option.description == "Name option"

    def test_from_integer(self) -> None:
        """Test creating option from integer factory method."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_integer(
            option_id=option_id,
            value=100,
            option_display_name="--port",
            description="Port number",
        )

        assert option.option_id == option_id
        assert option.value == 100
        assert option.value_type == EnumCliOptionValueType.INTEGER
        assert option.option_display_name == "--port"

    def test_from_float(self) -> None:
        """Test creating option from float factory method."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_float(
            option_id=option_id,
            value=2.5,
            option_display_name="--scale",
            description="Scale factor",
        )

        assert option.option_id == option_id
        assert option.value == 2.5
        assert option.value_type == EnumCliOptionValueType.FLOAT

    def test_from_boolean(self) -> None:
        """Test creating option from boolean factory method."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_boolean(
            option_id=option_id,
            value=False,
            option_display_name="--quiet",
            is_flag=True,
        )

        assert option.option_id == option_id
        assert option.value is False
        assert option.value_type == EnumCliOptionValueType.BOOLEAN
        assert option.is_flag is True

    def test_from_uuid(self) -> None:
        """Test creating option from UUID factory method."""
        option_id = uuid.uuid4()
        value_uuid = uuid.uuid4()
        option = ModelCliCommandOption.from_uuid(
            option_id=option_id,
            value=value_uuid,
            option_display_name="--session",
        )

        assert option.option_id == option_id
        assert option.value == value_uuid
        assert option.value_type == EnumCliOptionValueType.UUID

    def test_from_string_list(self) -> None:
        """Test creating option from string list factory method."""
        option_id = uuid.uuid4()
        tags = ["python", "test", "cli"]
        option = ModelCliCommandOption.from_string_list(
            option_id=option_id,
            value=tags,
            option_display_name="--tags",
            is_multiple=True,
        )

        assert option.option_id == option_id
        assert option.value == tags
        assert option.value_type == EnumCliOptionValueType.STRING_LIST
        assert option.is_multiple is True

    def test_factory_with_all_metadata(self) -> None:
        """Test factory method with all metadata fields."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_string(
            option_id=option_id,
            value="production",
            option_display_name="--env",
            is_required=True,
            description="Environment name",
            valid_choices=["dev", "staging", "production"],
        )

        assert option.is_required is True
        assert option.description == "Environment name"
        assert option.valid_choices == ["dev", "staging", "production"]

    def test_factory_with_invalid_kwarg_types(self) -> None:
        """Test factory method sanitizes invalid kwarg types."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_string(
            option_id=option_id,
            value="test",
            option_display_name=123,  # Wrong type - should be sanitized
            is_flag="yes",  # Wrong type - should be False
            valid_choices="not a list",  # Wrong type - should be []
        )

        # Should sanitize invalid types to defaults
        assert option.option_display_name is None  # Invalid type cleared
        assert option.is_flag is False
        assert option.valid_choices == []


class TestModelCliCommandOptionValueValidation:
    """Test value type validation and type flexibility."""

    def test_value_accepts_any_type_with_discriminator(self) -> None:
        """Test that value field accepts various types (validation is advisory)."""
        option_id = uuid.uuid4()

        # Value field uses 'object' type, so it accepts anything
        # The validator provides type checking but may not enforce strictly

        # String value with STRING type
        option1 = ModelCliCommandOption(
            option_id=option_id,
            value="test",
            value_type=EnumCliOptionValueType.STRING,
        )
        assert option1.value == "test"

        # Integer with INTEGER type
        option2 = ModelCliCommandOption(
            option_id=option_id,
            value=42,
            value_type=EnumCliOptionValueType.INTEGER,
        )
        assert option2.value == 42

    def test_validate_float_type_accepts_int_and_float(self) -> None:
        """Test FLOAT type accepts both int and float."""
        option_id = uuid.uuid4()

        # Float value
        option1 = ModelCliCommandOption(
            option_id=option_id,
            value=3.14,
            value_type=EnumCliOptionValueType.FLOAT,
        )
        assert option1.value == 3.14

        # Integer value (should be accepted for FLOAT type)
        option2 = ModelCliCommandOption(
            option_id=option_id,
            value=42,
            value_type=EnumCliOptionValueType.FLOAT,
        )
        assert option2.value == 42

    def test_value_type_discriminator_pattern(self) -> None:
        """Test that value_type acts as type discriminator."""
        option_id = uuid.uuid4()

        # Each value_type indicates expected value type
        string_opt = ModelCliCommandOption(
            option_id=option_id,
            value="text",
            value_type=EnumCliOptionValueType.STRING,
        )
        assert string_opt.value_type == EnumCliOptionValueType.STRING

        int_opt = ModelCliCommandOption(
            option_id=option_id,
            value=123,
            value_type=EnumCliOptionValueType.INTEGER,
        )
        assert int_opt.value_type == EnumCliOptionValueType.INTEGER

        bool_opt = ModelCliCommandOption(
            option_id=option_id,
            value=True,
            value_type=EnumCliOptionValueType.BOOLEAN,
        )
        assert bool_opt.value_type == EnumCliOptionValueType.BOOLEAN

    def test_string_list_value_type(self) -> None:
        """Test STRING_LIST value type with list values."""
        option_id = uuid.uuid4()

        option = ModelCliCommandOption(
            option_id=option_id,
            value=["a", "b", "c"],
            value_type=EnumCliOptionValueType.STRING_LIST,
        )

        assert option.value_type == EnumCliOptionValueType.STRING_LIST
        assert isinstance(option.value, list)
        assert len(option.value) == 3

    def test_uuid_value_type(self) -> None:
        """Test UUID value type with UUID values."""
        option_id = uuid.uuid4()
        value_uuid = uuid.uuid4()

        option = ModelCliCommandOption(
            option_id=option_id,
            value=value_uuid,
            value_type=EnumCliOptionValueType.UUID,
        )

        assert option.value_type == EnumCliOptionValueType.UUID
        assert isinstance(option.value, UUID)
        assert option.value == value_uuid


class TestModelCliCommandOptionMethods:
    """Test option methods and computed properties."""

    def test_get_string_value_from_string(self) -> None:
        """Test getting string representation of string value."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_string(option_id, "test")

        assert option.get_string_value() == "test"

    def test_get_string_value_from_integer(self) -> None:
        """Test getting string representation of integer value."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_integer(option_id, 42)

        assert option.get_string_value() == "42"

    def test_get_string_value_from_float(self) -> None:
        """Test getting string representation of float value."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_float(option_id, 3.14)

        assert option.get_string_value() == "3.14"

    def test_get_string_value_from_boolean(self) -> None:
        """Test getting string representation of boolean value."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_boolean(option_id, True)

        assert option.get_string_value() == "True"

    def test_get_string_value_from_list(self) -> None:
        """Test getting string representation of list value."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_string_list(
            option_id,
            ["a", "b", "c"],
        )

        assert option.get_string_value() == "a,b,c"

    def test_get_typed_value(self) -> None:
        """Test getting properly typed value."""
        option_id = uuid.uuid4()

        # String
        option1 = ModelCliCommandOption.from_string(option_id, "test")
        assert option1.get_typed_value() == "test"

        # Integer
        option2 = ModelCliCommandOption.from_integer(option_id, 42)
        assert option2.get_typed_value() == 42

        # List
        option3 = ModelCliCommandOption.from_string_list(option_id, ["a", "b"])
        assert option3.get_typed_value() == ["a", "b"]

    def test_is_boolean_flag_true(self) -> None:
        """Test is_boolean_flag returns True for boolean flags."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_boolean(
            option_id,
            True,
            is_flag=True,
        )

        assert option.is_boolean_flag() is True

    def test_is_boolean_flag_false_not_flag(self) -> None:
        """Test is_boolean_flag returns False when not flagged."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_boolean(
            option_id,
            True,
            is_flag=False,  # Not a flag
        )

        assert option.is_boolean_flag() is False

    def test_is_boolean_flag_false_not_boolean(self) -> None:
        """Test is_boolean_flag returns False for non-boolean types."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_string(
            option_id,
            "true",
            is_flag=True,  # Flagged but not boolean type
        )

        assert option.is_boolean_flag() is False

    def test_option_name_with_display_name(self) -> None:
        """Test option_name property with display name."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_string(
            option_id,
            "test",
            option_display_name="--verbose",
        )

        assert option.option_name == "--verbose"

    def test_option_name_without_display_name(self) -> None:
        """Test option_name property falls back to UUID."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_string(option_id, "test")

        expected = f"option_{str(option_id)[:8]}"
        assert option.option_name == expected


class TestModelCliCommandOptionProtocols:
    """Test protocol method implementations."""

    def test_serialize(self) -> None:
        """Test serialization to dictionary."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_string(
            option_id,
            "test_value",
            option_display_name="--test",
            is_required=True,
            description="Test option",
        )

        serialized = option.serialize()

        assert isinstance(serialized, dict)
        assert serialized["option_id"] == option_id
        assert serialized["value"] == "test_value"
        assert serialized["value_type"] == EnumCliOptionValueType.STRING
        assert serialized["is_required"] is True
        assert serialized["description"] == "Test option"

    def test_get_name(self) -> None:
        """Test getting name via Nameable protocol."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_string(option_id, "test")

        name = option.get_name()
        assert "ModelCliCommandOption" in name

    def test_set_name(self) -> None:
        """Test setting name via Nameable protocol."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_string(option_id, "test")

        option.set_name("CustomName")
        # Should not raise even though model has no name field

    def test_validate_instance(self) -> None:
        """Test instance validation."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_string(option_id, "test")

        assert option.validate_instance() is True


class TestModelCliCommandOptionEdgeCases:
    """Test edge cases and complex scenarios."""

    def test_round_trip_serialization(self) -> None:
        """Test serialization round-trip maintains data."""
        option_id = uuid.uuid4()
        original = ModelCliCommandOption.from_string(
            option_id,
            "original_value",
            option_display_name="--test",
            is_required=True,
            is_multiple=False,
            description="Test description",
            valid_choices=["a", "b", "c"],
        )

        serialized = original.serialize()
        restored = ModelCliCommandOption(**serialized)

        assert restored.option_id == original.option_id
        assert restored.value == original.value
        assert restored.value_type == original.value_type
        assert restored.option_display_name == original.option_display_name
        assert restored.is_required == original.is_required
        assert restored.description == original.description
        assert restored.valid_choices == original.valid_choices

    def test_empty_description_and_choices(self) -> None:
        """Test option with empty description and no choices."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_string(option_id, "test")

        assert option.description == ""
        assert option.valid_choices == []

    def test_multiple_options_same_display_name(self) -> None:
        """Test multiple options can have same display name (different IDs)."""
        display_name = "--config"

        option1 = ModelCliCommandOption.from_string(
            uuid.uuid4(),
            "value1",
            option_display_name=display_name,
        )
        option2 = ModelCliCommandOption.from_string(
            uuid.uuid4(),
            "value2",
            option_display_name=display_name,
        )

        assert option1.option_display_name == option2.option_display_name
        assert option1.option_id != option2.option_id

    def test_complex_metadata_combination(self) -> None:
        """Test option with complex metadata combination."""
        option_id = uuid.uuid4()
        option = ModelCliCommandOption.from_string_list(
            option_id,
            ["tag1", "tag2", "tag3"],
            option_display_name="--tags",
            is_required=True,
            is_multiple=True,
            description="Resource tags",
            valid_choices=["tag1", "tag2", "tag3", "tag4"],
        )

        assert option.is_required is True
        assert option.is_multiple is True
        assert len(option.valid_choices) == 4
        assert isinstance(option.value, list)
        assert len(option.value) == 3
