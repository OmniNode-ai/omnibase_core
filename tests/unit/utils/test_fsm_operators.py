"""
Unit tests for FSM string comparison operators.

Tests the string comparison operators in utils/fsm_operators.py
that are used for FSM condition evaluation.

Coverage targets:
- equals operator with same types
- equals operator with different types (type coercion)
- not_equals operator
- None handling
- Numeric string coercion
- Boolean string coercion
- Complex type coercion (lists, dicts)
- Operator dispatch function
- Error handling for invalid operators
"""

import pytest

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.fsm_operators import (
    evaluate_equals,
    evaluate_not_equals,
    evaluate_string_operator,
    is_string_operator,
)


class TestEvaluateEquals:
    """Test the evaluate_equals function."""

    def test_equals_same_strings(self) -> None:
        """Test equals with identical strings."""
        assert evaluate_equals("hello", "hello") is True
        assert evaluate_equals("", "") is True
        assert evaluate_equals("test", "test") is True

    def test_equals_different_strings(self) -> None:
        """Test equals with different strings."""
        assert evaluate_equals("hello", "world") is False
        assert evaluate_equals("test", "TEST") is False  # Case sensitive
        assert evaluate_equals("a", "b") is False

    def test_equals_integer_string_coercion(self) -> None:
        """Test equals with integer to string coercion.

        This is a documented footgun - integers are coerced to strings.
        """
        assert evaluate_equals(1, "1") is True
        assert evaluate_equals("1", 1) is True
        assert evaluate_equals(42, "42") is True
        assert evaluate_equals(0, "0") is True
        assert evaluate_equals(-1, "-1") is True

    def test_equals_float_string_coercion(self) -> None:
        """Test equals with float to string coercion."""
        assert evaluate_equals(1.0, "1.0") is True
        assert evaluate_equals(3.14, "3.14") is True
        # Note: float precision can affect string representation
        assert evaluate_equals(0.1, "0.1") is True

    def test_equals_none_handling(self) -> None:
        """Test equals with None values.

        None becomes "None" when coerced to string.
        """
        assert evaluate_equals(None, "None") is True
        assert evaluate_equals("None", None) is True
        assert evaluate_equals(None, None) is True
        # None != empty string
        assert evaluate_equals(None, "") is False

    def test_equals_boolean_string_coercion(self) -> None:
        """Test equals with boolean to string coercion.

        Booleans become "True" or "False" when coerced.
        """
        assert evaluate_equals(True, "True") is True
        assert evaluate_equals(False, "False") is True
        assert evaluate_equals("True", True) is True
        assert evaluate_equals("False", False) is True
        # Note: "true" (lowercase) != True
        assert evaluate_equals(True, "true") is False
        assert evaluate_equals(False, "false") is False

    def test_equals_list_string_coercion(self) -> None:
        """Test equals with list to string coercion.

        Lists become their repr() when coerced.
        """
        assert evaluate_equals([1, 2], "[1, 2]") is True
        assert evaluate_equals([], "[]") is True
        assert evaluate_equals([1, 2, 3], "[1, 2, 3]") is True

    def test_equals_dict_string_coercion(self) -> None:
        """Test equals with dict to string coercion.

        Dicts become their repr() when coerced.
        """
        assert evaluate_equals({"a": 1}, "{'a': 1}") is True
        assert evaluate_equals({}, "{}") is True

    def test_equals_empty_values(self) -> None:
        """Test equals with empty values."""
        assert evaluate_equals("", "") is True
        assert evaluate_equals(0, "") is False  # "0" != ""
        assert evaluate_equals([], "[]") is True
        assert evaluate_equals({}, "{}") is True


class TestEvaluateNotEquals:
    """Test the evaluate_not_equals function."""

    def test_not_equals_different_strings(self) -> None:
        """Test not_equals with different strings."""
        assert evaluate_not_equals("a", "b") is True
        assert evaluate_not_equals("hello", "world") is True
        assert evaluate_not_equals("test", "TEST") is True  # Case sensitive

    def test_not_equals_same_strings(self) -> None:
        """Test not_equals with identical strings."""
        assert evaluate_not_equals("hello", "hello") is False
        assert evaluate_not_equals("", "") is False
        assert evaluate_not_equals("test", "test") is False

    def test_not_equals_integer_string_coercion(self) -> None:
        """Test not_equals with integer to string coercion."""
        assert evaluate_not_equals(1, "1") is False  # Both become "1"
        assert evaluate_not_equals(1, 2) is True
        assert evaluate_not_equals(1, "2") is True

    def test_not_equals_none_handling(self) -> None:
        """Test not_equals with None values."""
        assert evaluate_not_equals(None, "None") is False
        assert evaluate_not_equals(None, None) is False
        assert evaluate_not_equals(None, "") is True  # "None" != ""
        assert evaluate_not_equals(None, "null") is True

    def test_not_equals_boolean_string_coercion(self) -> None:
        """Test not_equals with boolean to string coercion."""
        assert evaluate_not_equals(True, "True") is False
        assert evaluate_not_equals(False, "False") is False
        assert evaluate_not_equals(True, "False") is True
        assert evaluate_not_equals(False, "True") is True
        assert evaluate_not_equals(True, "true") is True  # Case sensitive


class TestTypeCoercionFootguns:
    """Test documented type coercion edge cases (footguns).

    These tests document the intentional but potentially surprising
    behavior of string coercion.
    """

    def test_numeric_zero_coercion(self) -> None:
        """Test that 0 equals "0" but not ""."""
        assert evaluate_equals(0, "0") is True
        assert evaluate_equals(0, "") is False
        assert evaluate_equals(0.0, "0.0") is True

    def test_boolean_integer_confusion(self) -> None:
        """Test boolean vs integer string representations.

        True becomes "True", not "1", even though bool(1) == True.
        """
        assert evaluate_equals(True, "True") is True
        assert evaluate_equals(True, "1") is False  # "True" != "1"
        assert evaluate_equals(False, "False") is True
        assert evaluate_equals(False, "0") is False  # "False" != "0"

    def test_none_vs_string_none(self) -> None:
        """Test None coercion to "None" string."""
        assert evaluate_equals(None, "None") is True
        assert evaluate_equals(None, "null") is False  # Not JSON null
        assert evaluate_equals(None, "nil") is False  # Not Ruby nil

    def test_whitespace_sensitivity(self) -> None:
        """Test that whitespace is preserved in comparison."""
        assert evaluate_equals("hello", "hello ") is False
        assert evaluate_equals(" hello", "hello") is False
        assert evaluate_equals("hello world", "hello  world") is False

    def test_mixed_type_comparisons(self) -> None:
        """Test various mixed type comparisons."""
        # Integer and string
        assert evaluate_equals(42, "42") is True
        assert evaluate_equals(-1, "-1") is True

        # Float and string
        assert evaluate_equals(3.14159, "3.14159") is True

        # List and string
        assert evaluate_equals(["a", "b"], "['a', 'b']") is True

        # Nested structures
        nested = {"list": [1, 2], "str": "test"}
        # Note: Dict order may vary, so we test specific cases
        assert evaluate_equals({}, "{}") is True

    def test_special_characters(self) -> None:
        """Test strings with special characters."""
        assert evaluate_equals("hello\nworld", "hello\nworld") is True
        assert evaluate_equals("hello\tworld", "hello\tworld") is True
        assert evaluate_equals("hello\\world", "hello\\world") is True


class TestIsStringOperator:
    """Test the is_string_operator function."""

    def test_valid_equals_operators(self) -> None:
        """Test that equals operators are recognized."""
        assert is_string_operator("equals") is True
        assert is_string_operator("==") is True

    def test_valid_not_equals_operators(self) -> None:
        """Test that not_equals operators are recognized."""
        assert is_string_operator("not_equals") is True
        assert is_string_operator("!=") is True

    def test_invalid_operators(self) -> None:
        """Test that non-string operators are not recognized."""
        assert is_string_operator("greater_than") is False
        assert is_string_operator(">") is False
        assert is_string_operator("<") is False
        assert is_string_operator("in") is False
        assert is_string_operator("contains") is False
        assert is_string_operator("matches") is False
        assert is_string_operator("invalid") is False

    def test_case_sensitivity(self) -> None:
        """Test that operator names are case sensitive."""
        assert is_string_operator("equals") is True
        assert is_string_operator("EQUALS") is False
        assert is_string_operator("Equals") is False


class TestEvaluateStringOperator:
    """Test the evaluate_string_operator dispatch function."""

    def test_dispatch_equals(self) -> None:
        """Test dispatch to equals operator."""
        assert evaluate_string_operator("equals", "a", "a") is True
        assert evaluate_string_operator("equals", "a", "b") is False
        assert evaluate_string_operator("==", "a", "a") is True
        assert evaluate_string_operator("==", 1, "1") is True

    def test_dispatch_not_equals(self) -> None:
        """Test dispatch to not_equals operator."""
        assert evaluate_string_operator("not_equals", "a", "b") is True
        assert evaluate_string_operator("not_equals", "a", "a") is False
        assert evaluate_string_operator("!=", "a", "b") is True
        assert evaluate_string_operator("!=", 1, "1") is False

    def test_dispatch_invalid_operator(self) -> None:
        """Test that invalid operators raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            evaluate_string_operator("invalid", "a", "b")

        assert "Unknown string operator" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)

    def test_dispatch_non_string_operator(self) -> None:
        """Test that non-string operators raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            evaluate_string_operator("greater_than", 1, 2)

        assert "Unknown string operator" in str(exc_info.value)

        with pytest.raises(ModelOnexError) as exc_info:
            evaluate_string_operator(">", 1, 2)

        assert "Unknown string operator" in str(exc_info.value)

    def test_dispatch_with_none_values(self) -> None:
        """Test dispatch with None values."""
        assert evaluate_string_operator("equals", None, "None") is True
        assert evaluate_string_operator("not_equals", None, "") is True

    def test_dispatch_with_type_coercion(self) -> None:
        """Test dispatch preserves type coercion behavior."""
        # Integer to string
        assert evaluate_string_operator("equals", 42, "42") is True
        assert evaluate_string_operator("!=", 42, "43") is True

        # Boolean to string
        assert evaluate_string_operator("==", True, "True") is True
        assert evaluate_string_operator("not_equals", False, "True") is True


class TestErrorMessages:
    """Test error messages and context."""

    def test_invalid_operator_error_context(self) -> None:
        """Test that error includes operator and valid operators."""
        with pytest.raises(ModelOnexError) as exc_info:
            evaluate_string_operator("bad_op", "a", "b")

        error = exc_info.value
        assert error.context is not None
        # ModelOnexError wraps context in additional_context.context
        inner_context = error.context.get("additional_context", {}).get("context", {})
        assert "operator" in inner_context
        assert inner_context["operator"] == "bad_op"
        assert "valid_operators" in inner_context


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_string_comparisons(self) -> None:
        """Test comparisons involving empty strings."""
        assert evaluate_equals("", "") is True
        assert evaluate_not_equals("", "") is False
        assert evaluate_equals("", " ") is False

    def test_unicode_strings(self) -> None:
        """Test comparisons with unicode strings."""
        assert evaluate_equals("cafe\u0301", "cafe\u0301") is True
        assert evaluate_equals("\u00e9", "\u00e9") is True  # e-acute

    def test_very_long_strings(self) -> None:
        """Test comparisons with very long strings."""
        long_str = "a" * 10000
        assert evaluate_equals(long_str, long_str) is True
        assert evaluate_not_equals(long_str, long_str + "b") is True

    def test_numeric_edge_cases(self) -> None:
        """Test numeric edge cases."""
        # Large numbers
        assert evaluate_equals(10**100, str(10**100)) is True

        # Negative numbers
        assert evaluate_equals(-42, "-42") is True

        # Scientific notation
        # Note: float string representation may use scientific notation
        assert evaluate_equals(1e10, str(1e10)) is True

    def test_callable_objects(self) -> None:
        """Test with callable objects (functions, lambdas)."""

        # Functions get their repr
        def my_func() -> None:
            pass

        result = str(my_func)
        assert evaluate_equals(my_func, result) is True

    def test_custom_object_with_str(self) -> None:
        """Test with custom object implementing __str__."""

        class CustomObj:
            def __str__(self) -> str:
                return "custom_string"

        obj = CustomObj()
        assert evaluate_equals(obj, "custom_string") is True
        assert evaluate_not_equals(obj, "other") is True
