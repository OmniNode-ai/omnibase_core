"""Tests for ModelValueChange model.

Tests the value change model used to represent differences between baseline
and replay output values.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.models.comparison import ModelValueChange


@pytest.mark.unit
class TestModelValueChangeCreation:
    """Test ModelValueChange creation and initialization."""

    def test_creation_with_required_fields_succeeds(self) -> None:
        """Model can be created with required old_value and new_value fields."""
        change = ModelValueChange(
            old_value="original text",
            new_value="updated text",
        )
        assert change.old_value == "original text"
        assert change.new_value == "updated text"

    def test_creation_with_numeric_string_values_succeeds(self) -> None:
        """Model can be created with numeric values serialized as strings."""
        change = ModelValueChange(
            old_value="42",
            new_value="100",
        )
        assert change.old_value == "42"
        assert change.new_value == "100"

    def test_creation_with_empty_strings_succeeds(self) -> None:
        """Model can be created with empty string values."""
        change = ModelValueChange(
            old_value="",
            new_value="",
        )
        assert change.old_value == ""
        assert change.new_value == ""

    def test_validation_fails_when_old_value_missing(self) -> None:
        """Validation fails if old_value is not provided."""
        with pytest.raises(ValidationError) as exc_info:
            ModelValueChange(new_value="some value")  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("old_value",) for e in errors)

    def test_validation_fails_when_new_value_missing(self) -> None:
        """Validation fails if new_value is not provided."""
        with pytest.raises(ValidationError) as exc_info:
            ModelValueChange(old_value="some value")  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("new_value",) for e in errors)


@pytest.mark.unit
class TestModelValueChangeImmutability:
    """Test immutability of ModelValueChange model."""

    def test_model_is_frozen_after_creation(self) -> None:
        """Model is immutable (frozen) after creation."""
        change = ModelValueChange(
            old_value="original",
            new_value="updated",
        )
        with pytest.raises(ValidationError):
            change.old_value = "modified"  # type: ignore[misc]
        with pytest.raises(ValidationError):
            change.new_value = "modified"  # type: ignore[misc]

    def test_model_can_be_hashed(self) -> None:
        """Frozen model can be used in sets and as dict keys."""
        change1 = ModelValueChange(
            old_value="original",
            new_value="updated",
        )
        change2 = ModelValueChange(
            old_value="original",
            new_value="updated",
        )
        # Can be added to set (requires hashability)
        change_set = {change1, change2}
        assert len(change_set) == 1  # Duplicates are removed


@pytest.mark.unit
class TestModelValueChangeSerialization:
    """Test serialization of ModelValueChange model."""

    def test_serialization_to_dict(self) -> None:
        """Model can be serialized to dictionary."""
        change = ModelValueChange(
            old_value="original",
            new_value="updated",
        )
        data = change.model_dump()
        assert isinstance(data, dict)
        assert data["old_value"] == "original"
        assert data["new_value"] == "updated"
        assert len(data) == 2

    def test_serialization_to_json(self) -> None:
        """Model can be serialized to JSON string."""
        change = ModelValueChange(
            old_value="original",
            new_value="updated",
        )
        json_str = change.model_dump_json()
        assert isinstance(json_str, str)
        assert '"old_value":"original"' in json_str
        assert '"new_value":"updated"' in json_str

    def test_deserialization_from_dict(self) -> None:
        """Model can be created from dictionary data."""
        data: dict[str, str] = {
            "old_value": "from dict original",
            "new_value": "from dict updated",
        }
        change = ModelValueChange(**data)
        assert change.old_value == "from dict original"
        assert change.new_value == "from dict updated"

    def test_model_validate_from_object_attributes(self) -> None:
        """Model can be created from object attributes via model_validate."""

        class ChangeData:
            """Mock object with change attributes."""

            def __init__(self) -> None:
                self.old_value = "attr original"
                self.new_value = "attr updated"

        change = ModelValueChange.model_validate(ChangeData())
        assert change.old_value == "attr original"
        assert change.new_value == "attr updated"


@pytest.mark.unit
class TestModelValueChangeValueTypes:
    """Test various value types that can be serialized to strings."""

    def test_handles_json_serialized_dict_values(self) -> None:
        """Model handles JSON-serialized dictionary values."""
        change = ModelValueChange(
            old_value='{"key": "old_value"}',
            new_value='{"key": "new_value"}',
        )
        assert change.old_value == '{"key": "old_value"}'
        assert change.new_value == '{"key": "new_value"}'

    def test_handles_json_serialized_list_values(self) -> None:
        """Model handles JSON-serialized list values."""
        change = ModelValueChange(
            old_value='["a", "b", "c"]',
            new_value='["x", "y", "z"]',
        )
        assert change.old_value == '["a", "b", "c"]'
        assert change.new_value == '["x", "y", "z"]'

    def test_handles_null_string_values(self) -> None:
        """Model handles 'null' as a string (serialized None)."""
        change = ModelValueChange(
            old_value="null",
            new_value="some value",
        )
        assert change.old_value == "null"
        assert change.new_value == "some value"

    def test_handles_boolean_string_values(self) -> None:
        """Model handles serialized boolean values."""
        change = ModelValueChange(
            old_value="true",
            new_value="false",
        )
        assert change.old_value == "true"
        assert change.new_value == "false"

    def test_handles_float_string_values(self) -> None:
        """Model handles serialized float values."""
        change = ModelValueChange(
            old_value="3.14159",
            new_value="2.71828",
        )
        assert change.old_value == "3.14159"
        assert change.new_value == "2.71828"

    def test_handles_multiline_string_values(self) -> None:
        """Model handles multiline string values."""
        change = ModelValueChange(
            old_value="line1\nline2\nline3",
            new_value="updated line1\nupdated line2",
        )
        assert "\n" in change.old_value
        assert "\n" in change.new_value


@pytest.mark.unit
class TestModelValueChangeEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_same_old_and_new_value_is_valid(self) -> None:
        """Model accepts identical old and new values."""
        change = ModelValueChange(
            old_value="same value",
            new_value="same value",
        )
        assert change.old_value == change.new_value

    def test_handles_unicode_characters(self) -> None:
        """Model handles unicode characters in values."""
        change = ModelValueChange(
            old_value="Hello, world!",
            new_value="Hello, world!",
        )
        assert change.old_value == "Hello, world!"
        assert change.new_value == "Hello, world!"

    def test_handles_special_characters(self) -> None:
        """Model handles special characters and escape sequences."""
        change = ModelValueChange(
            old_value='Tab:\t Newline:\n Quote:"',
            new_value="Backslash:\\ Null:\\0",
        )
        assert "\t" in change.old_value
        assert "\n" in change.old_value

    def test_handles_very_long_strings(self) -> None:
        """Model handles very long string values."""
        long_value = "x" * 10000
        change = ModelValueChange(
            old_value=long_value,
            new_value=long_value + "_modified",
        )
        assert len(change.old_value) == 10000
        assert len(change.new_value) == 10009

    def test_extra_fields_are_ignored(self) -> None:
        """Extra fields in input are ignored (ConfigDict extra='ignore')."""
        data: dict[str, Any] = {
            "old_value": "original",
            "new_value": "updated",
            "extra_field": "should be ignored",
        }
        change = ModelValueChange(**data)
        assert change.old_value == "original"
        assert not hasattr(change, "extra_field")


@pytest.mark.unit
class TestModelValueChangeEquality:
    """Test equality and comparison behavior."""

    def test_equality_when_same_values_returns_true(self) -> None:
        """Two instances with identical values are equal."""
        change1 = ModelValueChange(
            old_value="original",
            new_value="updated",
        )
        change2 = ModelValueChange(
            old_value="original",
            new_value="updated",
        )
        assert change1 == change2

    def test_equality_when_different_old_value_returns_false(self) -> None:
        """Two instances with different old_value are not equal."""
        change1 = ModelValueChange(
            old_value="original",
            new_value="updated",
        )
        change2 = ModelValueChange(
            old_value="different original",
            new_value="updated",
        )
        assert change1 != change2

    def test_equality_when_different_new_value_returns_false(self) -> None:
        """Two instances with different new_value are not equal."""
        change1 = ModelValueChange(
            old_value="original",
            new_value="updated",
        )
        change2 = ModelValueChange(
            old_value="original",
            new_value="different updated",
        )
        assert change1 != change2
