"""
Unit tests for FSM expression parser.

Tests the 3-token expression parser for FSM condition evaluation.
"""

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.fsm_expression_parser import (
    SUPPORTED_OPERATORS,
    get_supported_operators,
    parse_expression,
    validate_expression,
)


class TestParseExpressionValidExpressions:
    """Tests for valid 3-token expressions."""

    def test_simple_equals_expression(self) -> None:
        """Should parse simple equals expression."""
        field, operator, value = parse_expression("count equals 5")
        assert field == "count"
        assert operator == "equals"
        assert value == "5"

    def test_not_equals_expression(self) -> None:
        """Should parse not_equals expression."""
        field, operator, value = parse_expression("status not_equals pending")
        assert field == "status"
        assert operator == "not_equals"
        assert value == "pending"

    def test_greater_than_expression(self) -> None:
        """Should parse greater_than expression."""
        field, operator, value = parse_expression("age greater_than 18")
        assert field == "age"
        assert operator == "greater_than"
        assert value == "18"

    def test_less_than_expression(self) -> None:
        """Should parse less_than expression."""
        field, operator, value = parse_expression("priority less_than 10")
        assert field == "priority"
        assert operator == "less_than"
        assert value == "10"

    def test_greater_than_or_equal_expression(self) -> None:
        """Should parse greater_than_or_equal expression."""
        field, operator, value = parse_expression("score greater_than_or_equal 90")
        assert field == "score"
        assert operator == "greater_than_or_equal"
        assert value == "90"

    def test_less_than_or_equal_expression(self) -> None:
        """Should parse less_than_or_equal expression."""
        field, operator, value = parse_expression("retries less_than_or_equal 3")
        assert field == "retries"
        assert operator == "less_than_or_equal"
        assert value == "3"

    def test_min_length_expression(self) -> None:
        """Should parse min_length expression."""
        field, operator, value = parse_expression("data_sources min_length 1")
        assert field == "data_sources"
        assert operator == "min_length"
        assert value == "1"

    def test_max_length_expression(self) -> None:
        """Should parse max_length expression."""
        field, operator, value = parse_expression("items max_length 100")
        assert field == "items"
        assert operator == "max_length"
        assert value == "100"

    def test_exists_expression(self) -> None:
        """Should parse exists expression with placeholder value."""
        field, operator, value = parse_expression("name exists _")
        assert field == "name"
        assert operator == "exists"
        assert value == "_"

    def test_not_exists_expression(self) -> None:
        """Should parse not_exists expression."""
        field, operator, value = parse_expression("deleted_at not_exists _")
        assert field == "deleted_at"
        assert operator == "not_exists"
        assert value == "_"

    def test_in_expression(self) -> None:
        """Should parse in expression with comma-separated values."""
        field, operator, value = parse_expression("status in active,pending,processing")
        assert field == "status"
        assert operator == "in"
        assert value == "active,pending,processing"

    def test_not_in_expression(self) -> None:
        """Should parse not_in expression."""
        field, operator, value = parse_expression("state not_in error,failed")
        assert field == "state"
        assert operator == "not_in"
        assert value == "error,failed"

    def test_contains_expression(self) -> None:
        """Should parse contains expression."""
        field, operator, value = parse_expression("message contains error")
        assert field == "message"
        assert operator == "contains"
        assert value == "error"

    def test_matches_expression(self) -> None:
        """Should parse matches expression with regex pattern."""
        field, operator, value = parse_expression("email matches ^[a-z]+@")
        assert field == "email"
        assert operator == "matches"
        assert value == "^[a-z]+@"


class TestParseExpressionWhitespace:
    """Tests for whitespace handling."""

    def test_multiple_spaces_between_tokens(self) -> None:
        """Should handle multiple spaces between tokens."""
        field, operator, value = parse_expression("count    equals    5")
        assert field == "count"
        assert operator == "equals"
        assert value == "5"

    def test_leading_whitespace(self) -> None:
        """Should handle leading whitespace."""
        field, operator, value = parse_expression("   count equals 5")
        assert field == "count"
        assert operator == "equals"
        assert value == "5"

    def test_trailing_whitespace(self) -> None:
        """Should handle trailing whitespace."""
        field, operator, value = parse_expression("count equals 5   ")
        assert field == "count"
        assert operator == "equals"
        assert value == "5"

    def test_mixed_whitespace(self) -> None:
        """Should handle mixed leading, trailing, and internal whitespace."""
        field, operator, value = parse_expression("   count   equals   5   ")
        assert field == "count"
        assert operator == "equals"
        assert value == "5"

    def test_tab_as_separator(self) -> None:
        """Should handle tabs as whitespace separator."""
        field, operator, value = parse_expression("count\tequals\t5")
        assert field == "count"
        assert operator == "equals"
        assert value == "5"


class TestParseExpressionInvalidTokenCount:
    """Tests for rejection of incorrect token counts."""

    def test_empty_string(self) -> None:
        """Should reject empty string."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("")
        assert "cannot be empty" in str(exc_info.value)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_whitespace_only(self) -> None:
        """Should reject whitespace-only string."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("   ")
        assert "cannot be empty" in str(exc_info.value)

    def test_single_token(self) -> None:
        """Should reject single token."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("count")
        error = exc_info.value
        assert "exactly 3 tokens" in str(error)
        assert "got 1" in str(error)
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_two_tokens(self) -> None:
        """Should reject two tokens."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("count equals")
        error = exc_info.value
        assert "exactly 3 tokens" in str(error)
        assert "got 2" in str(error)

    def test_four_tokens(self) -> None:
        """Should reject four tokens."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("too many tokens here")
        error = exc_info.value
        assert "exactly 3 tokens" in str(error)
        assert "got 4" in str(error)

    def test_five_tokens(self) -> None:
        """Should reject five tokens."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("one two three four five")
        error = exc_info.value
        assert "exactly 3 tokens" in str(error)
        assert "got 5" in str(error)

    def test_many_tokens(self) -> None:
        """Should reject many tokens with clear error message."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("a b c d e f g h i j")
        error = exc_info.value
        assert "exactly 3 tokens" in str(error)
        assert "got 10" in str(error)


class TestParseExpressionUnsupportedOperator:
    """Tests for unsupported operator rejection."""

    def test_invalid_operator(self) -> None:
        """Should reject invalid operator."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("count invalid_op 5")
        error = exc_info.value
        assert "Unsupported operator" in str(error)
        assert "invalid_op" in str(error)
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_typo_in_operator(self) -> None:
        """Should reject typo in operator."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("count eqals 5")  # typo: eqals instead of equals
        assert "Unsupported operator" in str(exc_info.value)
        assert "eqals" in str(exc_info.value)

    def test_python_operator_not_supported(self) -> None:
        """Should reject Python comparison operators."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("count == 5")
        assert "Unsupported operator" in str(exc_info.value)

    def test_sql_operator_not_supported(self) -> None:
        """Should reject SQL-style operators."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("count LIKE pattern")
        assert "Unsupported operator" in str(exc_info.value)

    def test_case_sensitive_operator(self) -> None:
        """Should reject uppercase operators (case-sensitive)."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("count EQUALS 5")
        assert "Unsupported operator" in str(exc_info.value)
        assert "EQUALS" in str(exc_info.value)


class TestParseExpressionErrorContext:
    """Tests for error context information."""

    def test_error_includes_expression(self) -> None:
        """Should include original expression in error context."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("too many tokens here")
        # The error should contain the expression for debugging
        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_error_includes_token_count(self) -> None:
        """Should include token count in error message."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("a b c d e")
        assert "got 5" in str(exc_info.value)

    def test_error_includes_tokens(self) -> None:
        """Should include parsed tokens in error for debugging."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("a b")
        error_msg = str(exc_info.value)
        assert "2" in error_msg  # token count


class TestAllSupportedOperators:
    """Tests to verify all supported operators are accepted."""

    @pytest.mark.parametrize(
        "operator",
        [
            "equals",
            "not_equals",
            "greater_than",
            "less_than",
            "greater_than_or_equal",
            "less_than_or_equal",
            "min_length",
            "max_length",
            "exists",
            "not_exists",
            "in",
            "not_in",
            "contains",
            "matches",
        ],
    )
    def test_supported_operator(self, operator: str) -> None:
        """Should accept all supported operators."""
        field, op, value = parse_expression(f"field {operator} value")
        assert field == "field"
        assert op == operator
        assert value == "value"


class TestValidateExpression:
    """Tests for the validate_expression helper function."""

    def test_valid_expression_returns_true(self) -> None:
        """Should return True for valid expressions."""
        assert validate_expression("count equals 5") is True

    def test_empty_expression_returns_false(self) -> None:
        """Should return False for empty expression."""
        assert validate_expression("") is False

    def test_wrong_token_count_returns_false(self) -> None:
        """Should return False for wrong token count."""
        assert validate_expression("too many tokens here") is False

    def test_invalid_operator_returns_false(self) -> None:
        """Should return False for invalid operator."""
        assert validate_expression("count invalid_op 5") is False

    def test_all_supported_operators_valid(self) -> None:
        """Should return True for all supported operators."""
        for operator in SUPPORTED_OPERATORS:
            assert validate_expression(f"field {operator} value") is True


class TestGetSupportedOperators:
    """Tests for the get_supported_operators function."""

    def test_returns_frozenset(self) -> None:
        """Should return a frozenset."""
        result = get_supported_operators()
        assert isinstance(result, frozenset)

    def test_contains_expected_operators(self) -> None:
        """Should contain all expected operators."""
        operators = get_supported_operators()
        expected = {
            "equals",
            "not_equals",
            "greater_than",
            "less_than",
            "min_length",
            "max_length",
            "exists",
            "not_exists",
        }
        assert expected.issubset(operators)

    def test_same_as_module_constant(self) -> None:
        """Should return the same set as SUPPORTED_OPERATORS constant."""
        assert get_supported_operators() is SUPPORTED_OPERATORS


class TestSupportedOperatorsConstant:
    """Tests for the SUPPORTED_OPERATORS constant."""

    def test_is_frozenset(self) -> None:
        """Should be a frozenset (immutable)."""
        assert isinstance(SUPPORTED_OPERATORS, frozenset)

    def test_not_empty(self) -> None:
        """Should not be empty."""
        assert len(SUPPORTED_OPERATORS) > 0

    def test_contains_core_operators(self) -> None:
        """Should contain core comparison operators."""
        assert "equals" in SUPPORTED_OPERATORS
        assert "not_equals" in SUPPORTED_OPERATORS
        assert "greater_than" in SUPPORTED_OPERATORS
        assert "less_than" in SUPPORTED_OPERATORS

    def test_contains_length_operators(self) -> None:
        """Should contain length operators."""
        assert "min_length" in SUPPORTED_OPERATORS
        assert "max_length" in SUPPORTED_OPERATORS

    def test_contains_existence_operators(self) -> None:
        """Should contain existence operators."""
        assert "exists" in SUPPORTED_OPERATORS
        assert "not_exists" in SUPPORTED_OPERATORS


class TestEdgeCases:
    """Tests for edge cases and unusual inputs."""

    def test_numeric_field_name(self) -> None:
        """Should accept numeric-looking field names."""
        field, operator, value = parse_expression("123 equals abc")
        assert field == "123"
        assert operator == "equals"
        assert value == "abc"

    def test_underscore_field_name(self) -> None:
        """Should accept underscore in field names."""
        field, _operator, _value = parse_expression("my_field_name equals test")
        assert field == "my_field_name"

    def test_value_with_special_characters(self) -> None:
        """Should accept values with special characters."""
        _field, _operator, value = parse_expression("pattern matches ^[a-z]+$")
        assert value == "^[a-z]+$"

    def test_hyphenated_value(self) -> None:
        """Should accept hyphenated values."""
        _field, _operator, value = parse_expression("uuid equals abc-123-def")
        assert value == "abc-123-def"

    def test_empty_looking_value(self) -> None:
        """Should accept placeholder values like underscore."""
        _field, _operator, value = parse_expression("optional exists _")
        assert value == "_"

    def test_zero_value(self) -> None:
        """Should accept zero as value."""
        _field, _operator, value = parse_expression("count equals 0")
        assert value == "0"

    def test_negative_value(self) -> None:
        """Should accept negative numbers as values."""
        _field, _operator, value = parse_expression("temperature greater_than -10")
        assert value == "-10"

    def test_decimal_value(self) -> None:
        """Should accept decimal values."""
        _field, _operator, value = parse_expression("ratio less_than 0.5")
        assert value == "0.5"

    def test_boolean_looking_value(self) -> None:
        """Should accept boolean-looking strings as values."""
        _field, _operator, value = parse_expression("enabled equals true")
        assert value == "true"

    def test_camelcase_field_name(self) -> None:
        """Should accept camelCase field names."""
        field, _operator, _value = parse_expression("myFieldName equals test")
        assert field == "myFieldName"

    def test_dot_in_field_name(self) -> None:
        """Should accept dots in field names (nested path)."""
        field, _operator, _value = parse_expression("user.email exists _")
        assert field == "user.email"


class TestConsistencyWithFSMExecutor:
    """Tests ensuring consistency with fsm_executor condition evaluation."""

    def test_all_fsm_executor_operators_supported(self) -> None:
        """Should support all operators used in fsm_executor."""
        # These operators are used in fsm_executor._evaluate_single_condition()
        fsm_executor_operators = {
            "equals",
            "not_equals",
            "in",
            "not_in",
            "contains",
            "matches",
            # Note: fsm_executor also uses ==, !=, >, <, >=, <= but those are
            # symbol-based. Our parser uses word-based operators.
        }
        for op in fsm_executor_operators:
            assert op in SUPPORTED_OPERATORS, (
                f"Operator '{op}' not in SUPPORTED_OPERATORS"
            )
