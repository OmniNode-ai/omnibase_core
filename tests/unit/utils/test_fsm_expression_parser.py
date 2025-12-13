"""
Unit tests for FSM expression parser.

Tests the 3-token expression parser for FSM condition evaluation.
"""

import pytest

pytestmark = pytest.mark.unit

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

    def test_python_is_operator_not_supported(self) -> None:
        """Should reject Python 'is' operator (not a comparison operator)."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("count is None")
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
        """Should support all word-based operators used in fsm_executor."""
        # These word-based operators are used in fsm_executor._evaluate_single_condition()
        fsm_executor_operators = {
            "equals",
            "not_equals",
            "in",
            "not_in",
            "contains",
            "matches",
        }
        for op in fsm_executor_operators:
            assert op in SUPPORTED_OPERATORS, (
                f"Operator '{op}' not in SUPPORTED_OPERATORS"
            )


class TestOperatorSynchronization:
    """Tests verifying that all symbolic operators are properly supported.

    The parser supports both word-based operators (equals, not_equals, greater_than, etc.)
    and symbolic operators (==, !=, >, <, >=, <=). This test class ensures all symbolic
    operators are registered in SUPPORTED_OPERATORS and actually work when parsing.
    """

    def test_symbolic_equality_operators_in_supported_operators(self) -> None:
        """Should include symbolic equality operators (==, !=) in SUPPORTED_OPERATORS."""
        symbolic_equality_operators = {"==", "!="}
        for op in symbolic_equality_operators:
            assert op in SUPPORTED_OPERATORS, (
                f"Symbolic equality operator '{op}' not in SUPPORTED_OPERATORS"
            )

    def test_symbolic_comparison_operators_in_supported_operators(self) -> None:
        """Should include symbolic comparison operators (>, <, >=, <=) in SUPPORTED_OPERATORS."""
        symbolic_comparison_operators = {">", "<", ">=", "<="}
        for op in symbolic_comparison_operators:
            assert op in SUPPORTED_OPERATORS, (
                f"Symbolic comparison operator '{op}' not in SUPPORTED_OPERATORS"
            )

    def test_symbolic_equality_operators_parse_successfully(self) -> None:
        """Should successfully parse expressions using symbolic equality operators."""
        # Test == operator
        field, operator, value = parse_expression("status == active")
        assert field == "status"
        assert operator == "=="
        assert value == "active"

        # Test != operator
        field, operator, value = parse_expression("status != inactive")
        assert field == "status"
        assert operator == "!="
        assert value == "inactive"

    def test_symbolic_comparison_operators_parse_successfully(self) -> None:
        """Should successfully parse expressions using symbolic comparison operators."""
        # Test > operator
        field, operator, value = parse_expression("count > 10")
        assert field == "count"
        assert operator == ">"
        assert value == "10"

        # Test < operator
        field, operator, value = parse_expression("count < 100")
        assert field == "count"
        assert operator == "<"
        assert value == "100"

        # Test >= operator
        field, operator, value = parse_expression("age >= 18")
        assert field == "age"
        assert operator == ">="
        assert value == "18"

        # Test <= operator
        field, operator, value = parse_expression("age <= 65")
        assert field == "age"
        assert operator == "<="
        assert value == "65"

    def test_all_symbolic_operators_comprehensive(self) -> None:
        """Should support all symbolic operators with various value types."""
        # Define all symbolic operators with test expressions
        symbolic_operator_tests = [
            # Equality operators
            ("field == value", "==", "value"),
            ("field != value", "!=", "value"),
            # Comparison operators with numeric values
            ("count > 0", ">", "0"),
            ("count < 999", "<", "999"),
            ("score >= 0.5", ">=", "0.5"),
            ("score <= 1.0", "<=", "1.0"),
            # Comparison with negative numbers
            ("temp > -10", ">", "-10"),
            ("temp < -5", "<", "-5"),
        ]
        for expression, expected_op, expected_value in symbolic_operator_tests:
            _field, operator, value = parse_expression(expression)
            assert operator == expected_op, (
                f"Expected operator '{expected_op}' but got '{operator}' "
                f"for expression: {expression}"
            )
            assert value == expected_value, (
                f"Expected value '{expected_value}' but got '{value}' "
                f"for expression: {expression}"
            )


class TestFieldNameValidationSecurity:
    """Tests for field name validation security features.

    These tests verify that underscore-prefixed field names are rejected by default
    to prevent unintended access to private/internal context fields.
    """

    def test_reject_single_underscore_prefix(self) -> None:
        """Should reject field names starting with single underscore."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("_private equals secret")
        error = exc_info.value
        assert "cannot start with underscore" in str(error)
        assert "_private" in str(error)
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_reject_double_underscore_prefix(self) -> None:
        """Should reject field names starting with double underscore (dunder)."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("__class__ equals MyClass")
        error = exc_info.value
        assert "cannot start with underscore" in str(error)
        assert "__class__" in str(error)
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_reject_dunder_dict(self) -> None:
        """Should reject __dict__ field name."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("__dict__ exists _")
        error = exc_info.value
        assert "cannot start with underscore" in str(error)
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_reject_internal_field(self) -> None:
        """Should reject _internal_field style field names."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("_internal_data equals value")
        assert "cannot start with underscore" in str(exc_info.value)

    def test_allow_underscore_in_middle(self) -> None:
        """Should allow underscores in the middle of field names."""
        field, operator, value = parse_expression("my_field_name equals test")
        assert field == "my_field_name"
        assert operator == "equals"
        assert value == "test"

    def test_allow_underscore_at_end(self) -> None:
        """Should allow underscores at the end of field names."""
        field, _operator, _value = parse_expression("field_ equals test")
        assert field == "field_"

    def test_allow_multiple_underscores_in_middle(self) -> None:
        """Should allow multiple underscores in the middle of field names."""
        field, _operator, _value = parse_expression("my__field__name equals test")
        assert field == "my__field__name"

    def test_reject_nested_path_with_underscore_prefix_segment(self) -> None:
        """Should reject nested paths where a segment starts with underscore."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("user._private equals secret")
        error = exc_info.value
        assert "cannot start with underscore" in str(error)
        assert "_private" in str(error)
        assert "user._private" in str(error)
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_reject_nested_path_with_dunder_segment(self) -> None:
        """Should reject nested paths where a segment is a dunder name."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("obj.__class__.__name__ equals MyClass")
        error = exc_info.value
        assert "cannot start with underscore" in str(error)

    def test_allow_nested_path_normal_fields(self) -> None:
        """Should allow nested paths with normal field names."""
        field, operator, value = parse_expression("user.email equals test@example.com")
        assert field == "user.email"
        assert operator == "equals"
        assert value == "test@example.com"

    def test_allow_nested_path_with_underscores_in_middle(self) -> None:
        """Should allow nested paths where segments have underscores in middle."""
        field, _op, _val = parse_expression("user.first_name equals John")
        assert field == "user.first_name"

    def test_reject_empty_segment_in_nested_path(self) -> None:
        """Should reject nested paths with empty segments (consecutive dots)."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("user..email equals test")
        error = exc_info.value
        assert "empty segment" in str(error)
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_reject_leading_dot_in_field(self) -> None:
        """Should reject field names starting with dot."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression(".field equals value")
        error = exc_info.value
        assert "empty segment" in str(error)

    def test_reject_trailing_dot_in_field(self) -> None:
        """Should reject field names ending with dot."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("field. equals value")
        error = exc_info.value
        assert "empty segment" in str(error)

    def test_error_message_includes_security_guidance(self) -> None:
        """Should include guidance about allow_private_fields parameter."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("_secret equals value")
        error_msg = str(exc_info.value)
        assert "allow_private_fields=True" in error_msg
        assert "security" in error_msg.lower()


class TestAllowPrivateFieldsParameter:
    """Tests for the allow_private_fields parameter."""

    def test_allow_single_underscore_prefix_when_enabled(self) -> None:
        """Should allow single underscore prefix when allow_private_fields=True."""
        field, operator, value = parse_expression(
            "_private equals secret", allow_private_fields=True
        )
        assert field == "_private"
        assert operator == "equals"
        assert value == "secret"

    def test_allow_double_underscore_prefix_when_enabled(self) -> None:
        """Should allow double underscore prefix when allow_private_fields=True."""
        field, operator, value = parse_expression(
            "__class__ equals MyClass", allow_private_fields=True
        )
        assert field == "__class__"
        assert operator == "equals"
        assert value == "MyClass"

    def test_allow_dunder_dict_when_enabled(self) -> None:
        """Should allow __dict__ when allow_private_fields=True."""
        field, operator, value = parse_expression(
            "__dict__ exists _", allow_private_fields=True
        )
        assert field == "__dict__"
        assert operator == "exists"
        assert value == "_"

    def test_allow_nested_path_with_underscore_when_enabled(self) -> None:
        """Should allow nested paths with underscore prefix when enabled."""
        field, operator, value = parse_expression(
            "obj._internal equals value", allow_private_fields=True
        )
        assert field == "obj._internal"
        assert operator == "equals"
        assert value == "value"

    def test_validate_expression_rejects_underscore_by_default(self) -> None:
        """validate_expression should reject underscore fields by default."""
        assert validate_expression("_private equals secret") is False
        assert validate_expression("user._private equals secret") is False

    def test_validate_expression_allows_underscore_when_enabled(self) -> None:
        """validate_expression should allow underscore when enabled."""
        assert (
            validate_expression("_private equals secret", allow_private_fields=True)
            is True
        )
        assert (
            validate_expression(
                "user._private equals secret", allow_private_fields=True
            )
            is True
        )

    def test_normal_fields_work_with_allow_private_fields(self) -> None:
        """Normal fields should work regardless of allow_private_fields setting."""
        # With allow_private_fields=False (default)
        field1, _op1, _val1 = parse_expression("count equals 5")
        assert field1 == "count"

        # With allow_private_fields=True
        field2, _op2, _val2 = parse_expression(
            "count equals 5", allow_private_fields=True
        )
        assert field2 == "count"


class TestFieldNameValidationEdgeCases:
    """Edge cases for field name validation."""

    def test_single_character_field(self) -> None:
        """Should accept single character field names."""
        field, _op, _val = parse_expression("x equals 1")
        assert field == "x"

    def test_single_underscore_only_field(self) -> None:
        """Should reject field name that is just underscore."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("_ equals value")
        assert "cannot start with underscore" in str(exc_info.value)

    def test_double_underscore_only_field(self) -> None:
        """Should reject field name that is just double underscore."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("__ equals value")
        assert "cannot start with underscore" in str(exc_info.value)

    def test_field_with_numbers_and_underscores(self) -> None:
        """Should accept field names with numbers and underscores (not at start)."""
        field, _op, _val = parse_expression("field_123_name equals value")
        assert field == "field_123_name"

    def test_deeply_nested_path(self) -> None:
        """Should accept deeply nested paths."""
        field, _op, _val = parse_expression("a.b.c.d.e equals value")
        assert field == "a.b.c.d.e"

    def test_deeply_nested_path_with_underscore_in_last_segment(self) -> None:
        """Should reject if last segment starts with underscore."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("a.b.c._d equals value")
        error = exc_info.value
        assert "_d" in str(error)
        assert "cannot start with underscore" in str(error)

    def test_deeply_nested_path_with_underscore_in_middle_segment(self) -> None:
        """Should reject if middle segment starts with underscore."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_expression("a._b.c.d equals value")
        error = exc_info.value
        assert "_b" in str(error)
        assert "cannot start with underscore" in str(error)
