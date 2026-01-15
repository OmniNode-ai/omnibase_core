"""Unit tests for util_validators module.

This module tests the reusable Pydantic validator utilities that handle
common type conversions for frozen models in ONEX.
"""

from __future__ import annotations

from typing import Any

import pytest

from omnibase_core.utils.util_validators import (
    convert_dict_to_frozen_pairs,
    convert_list_to_tuple,
    ensure_timezone_aware,
)


class TestConvertListToTuple:
    """Tests for convert_list_to_tuple function."""

    def test_list_input_returns_tuple(self) -> None:
        """List input should be converted to tuple."""
        result = convert_list_to_tuple(["a", "b", "c"])
        assert result == ("a", "b", "c")
        assert isinstance(result, tuple)

    def test_tuple_input_passes_through(self) -> None:
        """Tuple input should pass through unchanged."""
        original = ("a", "b", "c")
        result = convert_list_to_tuple(original)
        assert result is original
        assert result == ("a", "b", "c")

    def test_empty_list_returns_empty_tuple(self) -> None:
        """Empty list should return empty tuple."""
        result = convert_list_to_tuple([])
        assert result == ()
        assert isinstance(result, tuple)

    def test_empty_tuple_passes_through(self) -> None:
        """Empty tuple should pass through unchanged."""
        original: tuple[str, ...] = ()
        result = convert_list_to_tuple(original)
        assert result is original
        assert result == ()

    def test_object_input_passes_through(self) -> None:
        """Non-list/tuple objects should pass through for Pydantic validation."""
        # Pydantic validates the final field type after the validator runs
        result = convert_list_to_tuple("not a list")
        assert result == "not a list"

    def test_none_input_passes_through(self) -> None:
        """None input should pass through for Pydantic validation."""
        result = convert_list_to_tuple(None)
        assert result is None

    def test_int_input_passes_through(self) -> None:
        """Integer input should pass through for Pydantic validation."""
        result = convert_list_to_tuple(42)
        assert result == 42

    def test_nested_lists_converts_outer_only(self) -> None:
        """Nested lists should only convert the outer list."""
        result = convert_list_to_tuple([["a", "b"], ["c", "d"]])
        assert result == (["a", "b"], ["c", "d"])
        assert isinstance(result, tuple)
        # Inner lists remain as lists
        assert isinstance(result[0], list)
        assert isinstance(result[1], list)

    def test_single_element_list(self) -> None:
        """Single element list should convert to single element tuple."""
        result = convert_list_to_tuple(["only"])
        assert result == ("only",)
        assert isinstance(result, tuple)
        assert len(result) == 1

    def test_single_element_tuple_passes_through(self) -> None:
        """Single element tuple should pass through."""
        original = ("only",)
        result = convert_list_to_tuple(original)
        assert result is original

    def test_list_with_integers(self) -> None:
        """List with integer elements should convert correctly."""
        result = convert_list_to_tuple([1, 2, 3, 4, 5])
        assert result == (1, 2, 3, 4, 5)
        assert isinstance(result, tuple)

    def test_list_with_mixed_types(self) -> None:
        """List with mixed types should convert correctly."""
        result = convert_list_to_tuple([1, "two", 3.0, None])
        assert result == (1, "two", 3.0, None)
        assert isinstance(result, tuple)

    def test_list_with_objects(self) -> None:
        """List with custom objects should convert correctly."""

        class CustomObject:
            def __init__(self, value: int) -> None:
                self.value = value

        obj1 = CustomObject(1)
        obj2 = CustomObject(2)
        result = convert_list_to_tuple([obj1, obj2])
        assert result == (obj1, obj2)
        assert isinstance(result, tuple)
        assert result[0] is obj1
        assert result[1] is obj2

    def test_list_with_unicode(self) -> None:
        """List with unicode strings should convert correctly."""
        result = convert_list_to_tuple(["hello", "world", "emoji"])
        assert result == ("hello", "world", "emoji")
        assert isinstance(result, tuple)

    def test_large_list_performance(self) -> None:
        """Large list should convert without performance issues."""
        large_list = list(range(10000))
        result = convert_list_to_tuple(large_list)
        assert len(result) == 10000
        assert isinstance(result, tuple)
        assert result[0] == 0
        assert result[-1] == 9999

    def test_dict_input_passes_through(self) -> None:
        """Dict input should pass through for Pydantic validation."""
        result = convert_list_to_tuple({"key": "value"})
        assert result == {"key": "value"}

    def test_preserves_element_identity(self) -> None:
        """Elements in the resulting tuple should maintain identity."""
        obj = object()
        result = convert_list_to_tuple([obj])
        assert result[0] is obj


class TestConvertDictToFrozenPairs:
    """Tests for convert_dict_to_frozen_pairs function."""

    def test_dict_input_returns_tuple_of_tuples(self) -> None:
        """Dict input should be converted to tuple of tuples."""
        result = convert_dict_to_frozen_pairs({"a": 1, "b": 2})
        assert isinstance(result, tuple)
        # Check all pairs are tuples
        for pair in result:
            assert isinstance(pair, tuple)
            assert len(pair) == 2
        # Check contents (order may vary without sort_keys)
        assert set(result) == {("a", 1), ("b", 2)}

    def test_dict_with_sort_keys_false_preserves_order(self) -> None:
        """Dict with sort_keys=False should preserve insertion order."""
        # Python 3.7+ guarantees dict insertion order
        d = {"z": 1, "a": 2, "m": 3}
        result = convert_dict_to_frozen_pairs(d, sort_keys=False)
        assert result == (("z", 1), ("a", 2), ("m", 3))

    def test_dict_with_sort_keys_true_sorts_by_key(self) -> None:
        """Dict with sort_keys=True should sort by key."""
        d = {"z": 1, "a": 2, "m": 3}
        result = convert_dict_to_frozen_pairs(d, sort_keys=True)
        assert result == (("a", 2), ("m", 3), ("z", 1))

    def test_tuple_input_passes_through(self) -> None:
        """Tuple of tuples input should pass through unchanged."""
        original = (("a", 1), ("b", 2))
        result = convert_dict_to_frozen_pairs(original)
        assert result is original

    def test_empty_dict_returns_empty_tuple(self) -> None:
        """Empty dict should return empty tuple."""
        result = convert_dict_to_frozen_pairs({})
        assert result == ()
        assert isinstance(result, tuple)

    def test_empty_tuple_passes_through(self) -> None:
        """Empty tuple should pass through unchanged."""
        original: tuple[tuple[str, int], ...] = ()
        result = convert_dict_to_frozen_pairs(original)
        assert result is original
        assert result == ()

    def test_object_input_passes_through(self) -> None:
        """Non-dict/tuple objects should pass through for Pydantic validation."""
        result = convert_dict_to_frozen_pairs("not a dict")
        assert result == "not a dict"

    def test_none_input_passes_through(self) -> None:
        """None input should pass through for Pydantic validation."""
        result = convert_dict_to_frozen_pairs(None)
        assert result is None

    def test_int_input_passes_through(self) -> None:
        """Integer input should pass through for Pydantic validation."""
        result = convert_dict_to_frozen_pairs(42)
        assert result == 42

    def test_list_input_passes_through(self) -> None:
        """List input should pass through for Pydantic validation."""
        result = convert_dict_to_frozen_pairs([("a", 1), ("b", 2)])
        assert result == [("a", 1), ("b", 2)]

    def test_single_entry_dict(self) -> None:
        """Single entry dict should convert correctly."""
        result = convert_dict_to_frozen_pairs({"only": "value"})
        assert result == (("only", "value"),)
        assert isinstance(result, tuple)
        assert len(result) == 1

    def test_dict_with_string_values(self) -> None:
        """Dict with string values should convert correctly."""
        result = convert_dict_to_frozen_pairs({"key1": "val1", "key2": "val2"})
        assert isinstance(result, tuple)
        assert set(result) == {("key1", "val1"), ("key2", "val2")}

    def test_dict_with_integer_values(self) -> None:
        """Dict with integer values should convert correctly."""
        result = convert_dict_to_frozen_pairs({"a": 1, "b": 2, "c": 3})
        assert isinstance(result, tuple)
        assert set(result) == {("a", 1), ("b", 2), ("c", 3)}

    def test_dict_with_nested_dict_values(self) -> None:
        """Dict with nested dict values should convert correctly."""
        nested: dict[str, Any] = {"outer": {"inner": "value"}}
        result = convert_dict_to_frozen_pairs(nested)
        assert result == (("outer", {"inner": "value"}),)
        # Inner dict remains as dict
        assert isinstance(result[0][1], dict)

    def test_dict_with_list_values(self) -> None:
        """Dict with list values should convert correctly."""
        result = convert_dict_to_frozen_pairs({"items": [1, 2, 3]})
        assert result == (("items", [1, 2, 3]),)
        # Value remains as list
        assert isinstance(result[0][1], list)

    def test_dict_with_none_values(self) -> None:
        """Dict with None values should convert correctly."""
        result = convert_dict_to_frozen_pairs({"nullable": None})
        assert result == (("nullable", None),)

    def test_dict_with_unicode_keys(self) -> None:
        """Dict with unicode keys should convert correctly."""
        result = convert_dict_to_frozen_pairs(
            {"key1": "value1", "key2": "value2"},
            sort_keys=True,
        )
        assert result == (("key1", "value1"), ("key2", "value2"))

    def test_dict_with_unicode_values(self) -> None:
        """Dict with unicode values should convert correctly."""
        result = convert_dict_to_frozen_pairs({"greeting": "Hello World!"})
        assert result == (("greeting", "Hello World!"),)

    def test_large_dict_performance(self) -> None:
        """Large dict should convert without performance issues."""
        large_dict = {f"key_{i}": i for i in range(10000)}
        result = convert_dict_to_frozen_pairs(large_dict)
        assert len(result) == 10000
        assert isinstance(result, tuple)

    def test_large_dict_sorted_performance(self) -> None:
        """Large dict with sort_keys=True should sort without issues."""
        large_dict = {f"key_{i}": i for i in range(10000)}
        result = convert_dict_to_frozen_pairs(large_dict, sort_keys=True)
        assert len(result) == 10000
        # Verify sorted order
        keys = [pair[0] for pair in result]
        assert keys == sorted(keys)

    def test_sort_keys_default_is_false(self) -> None:
        """sort_keys should default to False."""
        # Insertion order preserved
        d = {"z": 1, "a": 2}
        result = convert_dict_to_frozen_pairs(d)
        assert result == (("z", 1), ("a", 2))

    def test_preserves_value_identity(self) -> None:
        """Values in the resulting tuples should maintain identity."""
        obj = object()
        result = convert_dict_to_frozen_pairs({"key": obj})
        assert result[0][1] is obj

    def test_dict_with_mixed_value_types(self) -> None:
        """Dict with mixed value types should convert correctly."""
        d: dict[str, Any] = {
            "string": "hello",
            "int": 42,
            "float": 3.14,
            "none": None,
            "list": [1, 2],
            "dict": {"nested": True},
        }
        result = convert_dict_to_frozen_pairs(d, sort_keys=True)
        assert isinstance(result, tuple)
        assert len(result) == 6
        # Verify it's sorted by key
        keys = [pair[0] for pair in result]
        assert keys == sorted(keys)

    def test_numeric_string_keys_sort_lexicographically(self) -> None:
        """Numeric string keys should sort lexicographically, not numerically."""
        d = {"10": "ten", "2": "two", "1": "one"}
        result = convert_dict_to_frozen_pairs(d, sort_keys=True)
        # Lexicographic order: "1" < "10" < "2"
        assert result == (("1", "one"), ("10", "ten"), ("2", "two"))


class TestIntegrationWithPydantic:
    """Integration tests demonstrating Pydantic usage patterns."""

    def test_pydantic_model_with_list_validator(self) -> None:
        """Test convert_list_to_tuple in a Pydantic model context."""
        from pydantic import BaseModel, ConfigDict, field_validator

        class TestModel(BaseModel):
            model_config = ConfigDict(frozen=True)
            items: tuple[str, ...]

            @field_validator("items", mode="before")
            @classmethod
            def _convert_items(
                cls, v: list[str] | tuple[str, ...] | object
            ) -> tuple[str, ...]:
                return convert_list_to_tuple(v)

        # Test with list input (validator converts to tuple)
        model = TestModel(items=["a", "b", "c"])  # type: ignore[arg-type]
        assert model.items == ("a", "b", "c")
        assert isinstance(model.items, tuple)

        # Test with tuple input
        model2 = TestModel(items=("x", "y"))
        assert model2.items == ("x", "y")

    def test_pydantic_model_with_dict_validator(self) -> None:
        """Test convert_dict_to_frozen_pairs in a Pydantic model context."""
        from pydantic import BaseModel, ConfigDict, field_validator

        class TestModel(BaseModel):
            model_config = ConfigDict(frozen=True)
            properties: tuple[tuple[str, str], ...]

            @field_validator("properties", mode="before")
            @classmethod
            def _convert_properties(
                cls, v: dict[str, str] | tuple[tuple[str, str], ...] | object
            ) -> tuple[tuple[str, str], ...]:
                return convert_dict_to_frozen_pairs(v, sort_keys=True)

        # Test with dict input (validator converts to tuple of tuples)
        model = TestModel(properties={"b": "2", "a": "1"})  # type: ignore[arg-type]
        assert model.properties == (("a", "1"), ("b", "2"))
        assert isinstance(model.properties, tuple)

        # Test with tuple input
        model2 = TestModel(properties=(("x", "1"), ("y", "2")))
        assert model2.properties == (("x", "1"), ("y", "2"))

    def test_pydantic_model_frozen_immutability(self) -> None:
        """Test that converted values are truly immutable in frozen model."""
        from pydantic import BaseModel, ConfigDict, field_validator

        class TestModel(BaseModel):
            model_config = ConfigDict(frozen=True)
            items: tuple[str, ...]

            @field_validator("items", mode="before")
            @classmethod
            def _convert_items(
                cls, v: list[str] | tuple[str, ...] | object
            ) -> tuple[str, ...]:
                return convert_list_to_tuple(v)

        model = TestModel(items=["a", "b"])  # type: ignore[arg-type]

        # Attempting to modify should raise an error
        with pytest.raises(Exception):  # ValidationError or AttributeError
            model.items = ("x", "y")  # type: ignore[misc]


class TestEdgeCases:
    """Edge case tests for both converter functions."""

    def test_convert_list_with_duplicates(self) -> None:
        """List with duplicate elements should preserve all."""
        result = convert_list_to_tuple(["a", "a", "b", "b", "b"])
        assert result == ("a", "a", "b", "b", "b")
        assert len(result) == 5

    def test_convert_dict_duplicate_keys_last_wins(self) -> None:
        """Dict with 'duplicate' keys (via update) - last value wins."""
        d: dict[str, int] = {}
        d["key"] = 1
        d["key"] = 2  # Overwrites
        result = convert_dict_to_frozen_pairs(d)
        assert result == (("key", 2),)

    def test_convert_list_deeply_nested(self) -> None:
        """Deeply nested structure should only convert outer list."""
        # 4 levels of nesting: outer list converted to tuple, 3 inner lists remain
        nested: list[Any] = [[[["deep"]]]]
        result = convert_list_to_tuple(nested)
        # Outer list becomes tuple, inner [[["deep"]]] stays as list
        assert result == ([[["deep"]]],)
        assert isinstance(result, tuple)
        assert isinstance(result[0], list)

    def test_convert_dict_with_tuple_keys(self) -> None:
        """Dict with tuple keys should convert correctly if sortable."""
        d: dict[tuple[int, int], str] = {(1, 2): "a", (0, 1): "b"}
        result = convert_dict_to_frozen_pairs(d, sort_keys=True)
        # Tuples sort lexicographically
        assert result == (((0, 1), "b"), ((1, 2), "a"))

    def test_convert_dict_with_bool_values(self) -> None:
        """Dict with boolean values should convert correctly."""
        result = convert_dict_to_frozen_pairs({"enabled": True, "disabled": False})
        assert set(result) == {("enabled", True), ("disabled", False)}

    def test_convert_list_generator_not_converted(self) -> None:
        """Generator should pass through (not a list)."""
        gen = (x for x in range(3))
        result = convert_list_to_tuple(gen)
        # Generator is not a list, so it passes through
        assert result is gen

    def test_convert_dict_mapping_not_converted(self) -> None:
        """Non-dict Mapping should pass through."""
        from collections import OrderedDict

        od = OrderedDict([("a", 1), ("b", 2)])
        # OrderedDict is a dict subclass, so it WILL be converted
        result = convert_dict_to_frozen_pairs(od)
        assert result == (("a", 1), ("b", 2))

    def test_convert_list_set_not_converted(self) -> None:
        """Set should pass through (not a list)."""
        s = {1, 2, 3}
        result = convert_list_to_tuple(s)
        # Set is not a list, so it passes through
        assert result is s

    def test_convert_list_frozenset_not_converted(self) -> None:
        """Frozenset should pass through (not a list)."""
        fs = frozenset([1, 2, 3])
        result = convert_list_to_tuple(fs)
        # Frozenset is not a list, so it passes through
        assert result is fs


class TestEnsureTimezoneAware:
    """Tests for ensure_timezone_aware function."""

    def test_timezone_aware_datetime_passes_through(self) -> None:
        """Timezone-aware datetime should pass through unchanged."""
        from datetime import UTC, datetime

        dt = datetime.now(UTC)
        result = ensure_timezone_aware(dt, "timestamp")
        assert result is dt

    def test_naive_datetime_raises_value_error(self) -> None:
        """Naive datetime (tzinfo=None) should raise ValueError."""
        from datetime import datetime

        dt = datetime.now()
        with pytest.raises(ValueError, match="must be timezone-aware"):
            ensure_timezone_aware(dt, "timestamp")

    def test_error_message_includes_field_name(self) -> None:
        """Error message should include the field name."""
        from datetime import datetime

        dt = datetime.now()
        with pytest.raises(ValueError, match="custom_field must be timezone-aware"):
            ensure_timezone_aware(dt, "custom_field")

    def test_error_message_includes_datetime_value(self) -> None:
        """Error message should include the naive datetime value."""
        from datetime import datetime

        dt = datetime(2024, 1, 15, 10, 30, 0)
        with pytest.raises(ValueError, match="2024-01-15"):
            ensure_timezone_aware(dt, "timestamp")

    def test_effectively_naive_datetime_raises_value_error(self) -> None:
        """Datetime with tzinfo that returns None for utcoffset should raise."""
        from datetime import datetime, timedelta, tzinfo

        class NullOffsetTimezone(tzinfo):
            """A timezone that returns None for utcoffset (effectively naive)."""

            def utcoffset(self, dt: datetime | None) -> timedelta | None:
                return None

            def dst(self, dt: datetime | None) -> timedelta | None:
                return None

            def tzname(self, dt: datetime | None) -> str | None:
                return "NULL"

        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=NullOffsetTimezone())
        # tzinfo is set, but utcoffset() returns None - "effectively naive"
        assert dt.tzinfo is not None
        with pytest.raises(ValueError, match="effectively naive"):
            ensure_timezone_aware(dt, "timestamp")

    def test_valid_custom_timezone_passes(self) -> None:
        """Datetime with valid custom timezone should pass."""
        from datetime import datetime, timedelta, timezone

        # Create a custom timezone (UTC+5)
        custom_tz = timezone(timedelta(hours=5))
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=custom_tz)
        result = ensure_timezone_aware(dt, "timestamp")
        assert result is dt

    def test_utc_datetime_passes(self) -> None:
        """UTC datetime should pass validation."""
        from datetime import UTC, datetime

        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        result = ensure_timezone_aware(dt, "timestamp")
        assert result is dt

    def test_default_field_name_is_timestamp(self) -> None:
        """Default field_name should be 'timestamp'."""
        from datetime import datetime

        dt = datetime.now()
        with pytest.raises(ValueError, match="timestamp must be timezone-aware"):
            ensure_timezone_aware(dt)

    def test_various_field_names(self) -> None:
        """Function should work with various field names."""
        from datetime import datetime

        dt = datetime.now()
        field_names = ["created_at", "updated_at", "start_time", "end_time"]
        for field_name in field_names:
            with pytest.raises(
                ValueError, match=f"{field_name} must be timezone-aware"
            ):
                ensure_timezone_aware(dt, field_name)
