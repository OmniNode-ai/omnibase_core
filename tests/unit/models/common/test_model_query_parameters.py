"""
Tests for ModelQueryParameters.

This module tests the typed query parameters model including:
- Parameter value types (str, int, float, bool, list)
- Query string generation
- Type-safe accessors (get_string, get_int, get_float, get_bool)
- Security constraints (max parameter count)
"""

from __future__ import annotations

import pytest

from omnibase_core.models.common.model_query_parameters import (
    ModelQueryParameters,
    QueryParameterValue,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.mark.unit
class TestModelQueryParametersCreation:
    """Test ModelQueryParameters creation methods."""

    def test_empty_creation(self) -> None:
        """Test creating empty parameters."""
        params = ModelQueryParameters()
        assert len(params) == 0
        assert not params
        assert params.items == {}

    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        params = ModelQueryParameters.from_dict({"limit": 10, "offset": 0})
        assert params.items["limit"] == 10
        assert params.items["offset"] == 0

    def test_from_string_dict(self) -> None:
        """Test creating from string dictionary."""
        params = ModelQueryParameters.from_string_dict({"page": "1", "sort": "name"})
        assert params.items["page"] == "1"
        assert params.items["sort"] == "name"

    def test_mixed_types(self) -> None:
        """Test creating with mixed value types."""
        params = ModelQueryParameters.from_dict(
            {
                "name": "test",
                "count": 42,
                "ratio": 3.14,
                "active": True,
                "tags": ["a", "b", "c"],
            }
        )
        assert params.items["name"] == "test"
        assert params.items["count"] == 42
        assert params.items["ratio"] == 3.14
        assert params.items["active"] is True
        assert params.items["tags"] == ["a", "b", "c"]


@pytest.mark.unit
class TestModelQueryParametersConversion:
    """Test conversion methods."""

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        params = ModelQueryParameters.from_dict({"limit": 10, "active": True})
        result = params.to_dict()
        assert result == {"limit": 10, "active": True}
        # Ensure it's a copy
        result["limit"] = 20
        assert params.items["limit"] == 10

    def test_to_string_dict(self) -> None:
        """Test converting to string dictionary."""
        params = ModelQueryParameters.from_dict(
            {
                "limit": 10,
                "active": True,
                "ratio": 3.14,
            }
        )
        result = params.to_string_dict()
        assert result == {"limit": "10", "active": "true", "ratio": "3.14"}

    def test_to_string_dict_excludes_none(self) -> None:
        """Test that None values are excluded from string dict."""
        params = ModelQueryParameters.from_dict({"name": "test", "value": None})
        result = params.to_string_dict()
        assert result == {"name": "test"}

    def test_to_query_string(self) -> None:
        """Test query string generation."""
        params = ModelQueryParameters.from_dict({"page": 1, "limit": 10})
        result = params.to_query_string()
        # Order may vary, so check components
        assert "page=1" in result
        assert "limit=10" in result
        assert "&" in result

    def test_to_query_string_empty(self) -> None:
        """Test empty query string."""
        params = ModelQueryParameters()
        assert params.to_query_string() == ""

    def test_to_query_string_bool(self) -> None:
        """Test boolean values in query string."""
        params = ModelQueryParameters.from_dict({"active": True, "archived": False})
        result = params.to_query_string()
        assert "active=true" in result
        assert "archived=false" in result

    def test_to_query_string_list(self) -> None:
        """Test list values in query string."""
        params = ModelQueryParameters.from_dict({"tags": ["a", "b", "c"]})
        result = params.to_query_string()
        assert "tags=a%2Cb%2Cc" in result or "tags=a,b,c" in result


@pytest.mark.unit
class TestModelQueryParametersGetString:
    """Test get_string method."""

    def test_get_string_exists(self) -> None:
        """Test getting existing string value."""
        params = ModelQueryParameters.from_dict({"name": "test"})
        assert params.get_string("name") == "test"

    def test_get_string_missing(self) -> None:
        """Test getting missing string value returns default."""
        params = ModelQueryParameters()
        assert params.get_string("name") is None
        assert params.get_string("name", "default") == "default"

    def test_get_string_converts_int(self) -> None:
        """Test getting int value as string."""
        params = ModelQueryParameters.from_dict({"count": 42})
        assert params.get_string("count") == "42"

    def test_get_string_converts_bool(self) -> None:
        """Test getting bool value as string."""
        params = ModelQueryParameters.from_dict({"active": True, "archived": False})
        assert params.get_string("active") == "true"
        assert params.get_string("archived") == "false"


@pytest.mark.unit
class TestModelQueryParametersGetInt:
    """Test get_int method."""

    def test_get_int_exists(self) -> None:
        """Test getting existing int value."""
        params = ModelQueryParameters.from_dict({"count": 42})
        assert params.get_int("count") == 42

    def test_get_int_missing(self) -> None:
        """Test getting missing int value returns default."""
        params = ModelQueryParameters()
        assert params.get_int("count") is None
        assert params.get_int("count", 0) == 0

    def test_get_int_from_string(self) -> None:
        """Test getting int from string value."""
        params = ModelQueryParameters.from_dict({"count": "42"})
        assert params.get_int("count") == 42

    def test_get_int_invalid_string(self) -> None:
        """Test getting int from invalid string returns default."""
        params = ModelQueryParameters.from_dict({"count": "not_a_number"})
        assert params.get_int("count") is None
        assert params.get_int("count", 0) == 0

    def test_get_int_bool_returns_default(self) -> None:
        """Test getting int from bool returns default (bool is not int for this purpose)."""
        params = ModelQueryParameters.from_dict({"flag": True})
        # bool is subclass of int, but we explicitly exclude it
        assert params.get_int("flag") is None


@pytest.mark.unit
class TestModelQueryParametersGetFloat:
    """Test get_float method."""

    def test_get_float_exists(self) -> None:
        """Test getting existing float value."""
        params = ModelQueryParameters.from_dict({"ratio": 3.14})
        assert params.get_float("ratio") == 3.14

    def test_get_float_missing(self) -> None:
        """Test getting missing float value returns default."""
        params = ModelQueryParameters()
        assert params.get_float("ratio") is None
        assert params.get_float("ratio", 0.0) == 0.0

    def test_get_float_from_int(self) -> None:
        """Test getting float from int value."""
        params = ModelQueryParameters.from_dict({"count": 42})
        assert params.get_float("count") == 42.0

    def test_get_float_from_string(self) -> None:
        """Test getting float from string value."""
        params = ModelQueryParameters.from_dict({"ratio": "3.14"})
        assert params.get_float("ratio") == 3.14

    def test_get_float_invalid_string(self) -> None:
        """Test getting float from invalid string returns default."""
        params = ModelQueryParameters.from_dict({"ratio": "not_a_number"})
        assert params.get_float("ratio") is None
        assert params.get_float("ratio", 0.0) == 0.0


@pytest.mark.unit
class TestModelQueryParametersGetBool:
    """Test get_bool method."""

    def test_get_bool_true_values(self) -> None:
        """Test getting True from various truthy strings."""
        truthy_values = ["true", "True", "TRUE", "1", "yes", "YES", "on", "ON"]
        for val in truthy_values:
            params = ModelQueryParameters.from_dict({"flag": val})
            assert params.get_bool("flag") is True, f"Expected True for '{val}'"

    def test_get_bool_false_values(self) -> None:
        """Test getting False from various falsy strings."""
        falsy_values = ["false", "False", "FALSE", "0", "no", "NO", "off", "OFF"]
        for val in falsy_values:
            params = ModelQueryParameters.from_dict({"flag": val})
            assert params.get_bool("flag") is False, f"Expected False for '{val}'"

    def test_get_bool_missing(self) -> None:
        """Test getting missing bool value returns default."""
        params = ModelQueryParameters()
        assert params.get_bool("flag") is None
        assert params.get_bool("flag", True) is True
        assert params.get_bool("flag", False) is False

    def test_get_bool_actual_bool(self) -> None:
        """Test getting actual boolean value."""
        params = ModelQueryParameters.from_dict({"active": True, "archived": False})
        assert params.get_bool("active") is True
        assert params.get_bool("archived") is False

    def test_get_bool_from_int(self) -> None:
        """Test getting bool from int value."""
        params = ModelQueryParameters.from_dict({"flag": 1, "zero": 0, "negative": -1})
        assert params.get_bool("flag") is True
        assert params.get_bool("zero") is False
        assert params.get_bool("negative") is True

    def test_get_bool_unrecognized_string_returns_default(self) -> None:
        """Test that unrecognized strings return default, not False.

        This is a critical behavior: when a string value cannot be parsed
        as a boolean (e.g., "maybe", "unknown", "abc"), the method should
        return the provided default value, not hardcode False.

        PR #186 review feedback: Ensure unrecognized strings return default.
        """
        unrecognized_values = [
            "maybe",
            "unknown",
            "abc",
            "TRUE1",
            "FALSEE",
            "2",
            "-1",
            "",
            "  ",  # whitespace only
            "yesno",
            "truefalse",
        ]
        for val in unrecognized_values:
            params = ModelQueryParameters.from_dict({"flag": val})
            # With default=True, should return True (not False!)
            assert params.get_bool("flag", default=True) is True, (
                f"Expected True for unrecognized string '{val}' with default=True"
            )
            # With default=None, should return None
            assert params.get_bool("flag", default=None) is None, (
                f"Expected None for unrecognized string '{val}' with default=None"
            )
            # With default=False, should return False
            assert params.get_bool("flag", default=False) is False, (
                f"Expected False for unrecognized string '{val}' with default=False"
            )

    def test_get_bool_whitespace_handling(self) -> None:
        """Test that whitespace is properly stripped."""
        params = ModelQueryParameters.from_dict({"flag": "  true  "})
        assert params.get_bool("flag") is True

        params = ModelQueryParameters.from_dict({"flag": "  false  "})
        assert params.get_bool("flag") is False


@pytest.mark.unit
class TestModelQueryParametersOperations:
    """Test parameter operations."""

    def test_has(self) -> None:
        """Test has method."""
        params = ModelQueryParameters.from_dict({"name": "test"})
        assert params.has("name") is True
        assert params.has("missing") is False

    def test_contains(self) -> None:
        """Test __contains__ dunder."""
        params = ModelQueryParameters.from_dict({"name": "test"})
        assert "name" in params
        assert "missing" not in params

    def test_set(self) -> None:
        """Test set returns new instance."""
        params = ModelQueryParameters.from_dict({"a": 1})
        new_params = params.set("b", 2)

        # Original unchanged
        assert "b" not in params
        assert params.items["a"] == 1

        # New has both
        assert new_params.items["a"] == 1
        assert new_params.items["b"] == 2

    def test_remove(self) -> None:
        """Test remove returns new instance."""
        params = ModelQueryParameters.from_dict({"a": 1, "b": 2})
        new_params = params.remove("a")

        # Original unchanged
        assert "a" in params
        assert "b" in params

        # New without a
        assert "a" not in new_params
        assert "b" in new_params

    def test_remove_missing_key(self) -> None:
        """Test removing non-existent key is no-op."""
        params = ModelQueryParameters.from_dict({"a": 1})
        new_params = params.remove("missing")
        assert new_params.items == {"a": 1}


@pytest.mark.unit
class TestModelQueryParametersSecurity:
    """Test security constraints."""

    def test_max_parameters_exceeded(self) -> None:
        """Test that exceeding max parameters raises error."""
        # Create dict with MAX_PARAMETERS + 1 items
        large_dict: dict[str, QueryParameterValue] = {
            f"key_{i}": i for i in range(ModelQueryParameters.MAX_PARAMETERS + 1)
        }
        with pytest.raises(ModelOnexError) as exc_info:
            ModelQueryParameters.from_dict(large_dict)

        assert "exceeds maximum" in str(exc_info.value.message)

    def test_max_parameters_exactly(self) -> None:
        """Test that exactly max parameters is allowed."""
        exact_dict: dict[str, QueryParameterValue] = {
            f"key_{i}": i for i in range(ModelQueryParameters.MAX_PARAMETERS)
        }
        params = ModelQueryParameters.from_dict(exact_dict)
        assert len(params) == ModelQueryParameters.MAX_PARAMETERS


@pytest.mark.unit
class TestModelQueryParametersDunder:
    """Test dunder methods."""

    def test_len(self) -> None:
        """Test __len__."""
        params = ModelQueryParameters.from_dict({"a": 1, "b": 2, "c": 3})
        assert len(params) == 3

    def test_bool_true(self) -> None:
        """Test __bool__ with parameters."""
        params = ModelQueryParameters.from_dict({"a": 1})
        assert bool(params) is True

    def test_bool_false(self) -> None:
        """Test __bool__ without parameters."""
        params = ModelQueryParameters()
        assert bool(params) is False

    def test_bool_idiomatic_check_with_params(self) -> None:
        """Test idiomatic if check when parameters exist."""
        params = ModelQueryParameters.from_dict({"page": 1})
        assert params  # Idiomatic check should pass

    def test_bool_idiomatic_check_empty(self) -> None:
        """Test idiomatic if check when empty."""
        params = ModelQueryParameters()
        assert not params  # Idiomatic check should pass

    def test_bool_differs_from_standard_pydantic(self) -> None:
        """Test that __bool__ differs from standard Pydantic behavior.

        Standard Pydantic models always return True for bool(model) because
        the instance exists. ModelQueryParameters overrides this to return
        False when items is empty.
        """
        empty = ModelQueryParameters()
        # Standard Pydantic would return True here, but we return False
        assert bool(empty) is False

        with_params = ModelQueryParameters.from_dict({"limit": 10})
        assert bool(with_params) is True

    def test_bool_with_multiple_params(self) -> None:
        """Test bool() with multiple parameters."""
        params = ModelQueryParameters.from_dict(
            {
                "page": 1,
                "limit": 10,
                "sort": "name",
                "order": "asc",
            }
        )
        assert bool(params) is True
        assert params  # Idiomatic check
