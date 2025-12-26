"""Tests for ModelOptionalString.

This module tests the ModelOptionalString model including:
- Basic creation and field access
- Custom __bool__ behavior for idiomatic presence checks
- Value manipulation methods (get, set, map)
- Edge cases (empty string vs None)
"""

import pytest

from omnibase_core.models.core.model_optional_string import ModelOptionalString


@pytest.mark.unit
class TestModelOptionalStringCreation:
    """Test ModelOptionalString creation."""

    def test_create_with_value(self) -> None:
        """Test creating optional string with a value."""
        opt = ModelOptionalString(value="hello")
        assert opt.value == "hello"

    def test_create_with_none(self) -> None:
        """Test creating optional string with None."""
        opt = ModelOptionalString(value=None)
        assert opt.value is None

    def test_create_without_value_defaults_to_none(self) -> None:
        """Test creating optional string without value defaults to None."""
        opt = ModelOptionalString()
        assert opt.value is None

    def test_create_with_empty_string(self) -> None:
        """Test creating optional string with empty string."""
        opt = ModelOptionalString(value="")
        assert opt.value == ""


@pytest.mark.unit
class TestModelOptionalStringBoolConversion:
    """Tests for __bool__ behavior in ModelOptionalString.

    ModelOptionalString overrides the default Pydantic __bool__ behavior
    to return True when value is present (not None), enabling idiomatic
    presence checks like `if opt:` instead of `if opt.value is not None:`.

    IMPORTANT: Empty string ("") is a valid value and returns True,
    because __bool__ checks for presence, not truthiness of the value.
    """

    def test_bool_conversion_with_value(self) -> None:
        """Test __bool__ returns True when value is present."""
        opt = ModelOptionalString(value="hello")
        assert bool(opt) is True

    def test_bool_conversion_with_none(self) -> None:
        """Test __bool__ returns False when value is None."""
        opt = ModelOptionalString(value=None)
        assert bool(opt) is False

    def test_bool_conversion_with_empty_string(self) -> None:
        """Test __bool__ returns True for empty string (has value, even if empty).

        This is a critical edge case: empty string "" is a valid value,
        so bool(opt) should return True because a value IS present.
        This differs from Python's standard bool("") which returns False.
        """
        opt = ModelOptionalString(value="")
        assert bool(opt) is True

    def test_idiomatic_check_with_value(self) -> None:
        """Test idiomatic if check when value is present."""
        opt = ModelOptionalString(value="hello")
        assert opt  # Idiomatic check should pass

    def test_idiomatic_check_with_none(self) -> None:
        """Test idiomatic if check when value is None."""
        opt = ModelOptionalString(value=None)
        assert not opt  # Idiomatic check should pass

    def test_bool_in_if_statement_with_value(self) -> None:
        """Test boolean conversion in if statement when value present."""
        opt = ModelOptionalString(value="world")
        executed = False
        if opt:
            executed = True
        assert executed is True

    def test_bool_in_if_statement_with_none(self) -> None:
        """Test boolean conversion in if statement when value is None."""
        opt = ModelOptionalString(value=None)
        executed = False
        if opt:
            executed = True
        assert executed is False

    def test_bool_differs_from_standard_pydantic(self) -> None:
        """Test that __bool__ differs from standard Pydantic behavior.

        Standard Pydantic models always return True for bool(model) because
        the instance exists. ModelOptionalString overrides this to return
        False when value is None, enabling presence checks.
        """
        none_opt = ModelOptionalString(value=None)
        # Standard Pydantic would return True here, but we return False
        assert bool(none_opt) is False

        value_opt = ModelOptionalString(value="test")
        assert bool(value_opt) is True


@pytest.mark.unit
class TestModelOptionalStringHasValue:
    """Test has_value method."""

    def test_has_value_with_value(self) -> None:
        """Test has_value returns True when value is present."""
        opt = ModelOptionalString(value="hello")
        assert opt.has_value() is True

    def test_has_value_with_none(self) -> None:
        """Test has_value returns False when value is None."""
        opt = ModelOptionalString(value=None)
        assert opt.has_value() is False

    def test_has_value_with_empty_string(self) -> None:
        """Test has_value returns True for empty string."""
        opt = ModelOptionalString(value="")
        assert opt.has_value() is True

    def test_has_value_matches_bool(self) -> None:
        """Test that has_value() matches bool() behavior."""
        test_values = ["hello", "", None, "test", "  "]
        for val in test_values:
            opt = ModelOptionalString(value=val)
            assert opt.has_value() == bool(opt), f"Mismatch for value: {val!r}"


@pytest.mark.unit
class TestModelOptionalStringGetSet:
    """Test get and set methods."""

    def test_get_with_value(self) -> None:
        """Test get returns value when present."""
        opt = ModelOptionalString(value="hello")
        assert opt.get() == "hello"

    def test_get_with_none(self) -> None:
        """Test get returns None when no value."""
        opt = ModelOptionalString(value=None)
        assert opt.get() is None

    def test_set_value(self) -> None:
        """Test set updates value."""
        opt = ModelOptionalString(value=None)
        opt.set("new_value")
        assert opt.value == "new_value"

    def test_set_none(self) -> None:
        """Test set can clear value to None."""
        opt = ModelOptionalString(value="hello")
        opt.set(None)
        assert opt.value is None

    def test_get_or_default_with_value(self) -> None:
        """Test get_or_default returns value when present."""
        opt = ModelOptionalString(value="hello")
        assert opt.get_or_default("default") == "hello"

    def test_get_or_default_with_none(self) -> None:
        """Test get_or_default returns default when None."""
        opt = ModelOptionalString(value=None)
        assert opt.get_or_default("default") == "default"

    def test_get_or_default_with_empty_string(self) -> None:
        """Test get_or_default returns empty string (not default) when value is ""."""
        opt = ModelOptionalString(value="")
        assert opt.get_or_default("default") == ""


@pytest.mark.unit
class TestModelOptionalStringMap:
    """Test map transformation method."""

    def test_map_with_value(self) -> None:
        """Test map applies function when value present."""
        opt = ModelOptionalString(value="hello")
        result = opt.map(str.upper)
        assert result.value == "HELLO"

    def test_map_with_none(self) -> None:
        """Test map returns self when value is None."""
        opt = ModelOptionalString(value=None)
        result = opt.map(str.upper)
        assert result.value is None

    def test_map_with_empty_string(self) -> None:
        """Test map applies function to empty string."""
        opt = ModelOptionalString(value="")
        result = opt.map(lambda s: s + "suffix")
        assert result.value == "suffix"

    def test_map_chain(self) -> None:
        """Test chaining multiple map operations."""
        opt = ModelOptionalString(value="hello world")
        result = opt.map(str.upper).map(lambda s: s.replace(" ", "_"))
        assert result.value == "HELLO_WORLD"


@pytest.mark.unit
class TestModelOptionalStringSerialization:
    """Test ModelOptionalString serialization."""

    def test_model_dump_with_value(self) -> None:
        """Test model_dump with value."""
        opt = ModelOptionalString(value="test")
        data = opt.model_dump()
        assert data["value"] == "test"

    def test_model_dump_with_none(self) -> None:
        """Test model_dump with None."""
        opt = ModelOptionalString(value=None)
        data = opt.model_dump()
        assert data["value"] is None

    def test_round_trip_serialization(self) -> None:
        """Test round-trip serialization preserves value."""
        original_value = ModelOptionalString(value="test")
        original_none = ModelOptionalString(value=None)
        original_empty = ModelOptionalString(value="")

        restored_value = ModelOptionalString(**original_value.model_dump())
        restored_none = ModelOptionalString(**original_none.model_dump())
        restored_empty = ModelOptionalString(**original_empty.model_dump())

        assert bool(restored_value) is True
        assert bool(restored_none) is False
        assert bool(restored_empty) is True  # Empty string is still a value


@pytest.mark.unit
class TestModelOptionalStringEdgeCases:
    """Test edge cases for ModelOptionalString."""

    def test_whitespace_string(self) -> None:
        """Test string with only whitespace."""
        opt = ModelOptionalString(value="   ")
        assert bool(opt) is True  # Whitespace is still a value
        assert opt.has_value() is True

    def test_newline_string(self) -> None:
        """Test string with newlines."""
        opt = ModelOptionalString(value="hello\nworld\n")
        assert bool(opt) is True
        assert opt.has_value() is True
        assert "\n" in opt.value  # Verify actual newline character present

    def test_unicode_string(self) -> None:
        """Test string with unicode characters."""
        # Test with various unicode: Japanese, accented chars, emoji, Chinese
        unicode_value = (
            "\u3053\u3093\u306b\u3061\u306f \u00d1o\u00f1o \U0001f389 \u4e2d\u6587"
        )
        opt = ModelOptionalString(value=unicode_value)
        assert bool(opt) is True
        assert opt.value == unicode_value
        assert opt.has_value() is True
        # Verify non-ASCII characters are present
        assert any(ord(c) > 127 for c in opt.value)

    def test_long_string(self) -> None:
        """Test very long string."""
        long_value = "x" * 10000
        opt = ModelOptionalString(value=long_value)
        assert bool(opt) is True
        assert opt.value == long_value

    def test_special_characters(self) -> None:
        """Test string with special characters."""
        opt = ModelOptionalString(value="<script>alert('test')</script>")
        assert bool(opt) is True
        assert opt.has_value() is True
