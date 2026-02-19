# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelFSMTransitionCondition.

Tests all aspects of the FSM transition condition model including:
- Model instantiation and validation
- Default values (required=True, optional fields=None)
- Type validation for each field
- Protocol implementations (execute, serialize, validate_instance)
- Serialization/deserialization
- Edge cases (empty strings, special characters)
"""

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.fsm.model_fsm_transition_condition import (
    ModelFSMTransitionCondition,
)


@pytest.mark.unit
class TestModelFSMTransitionConditionInstantiation:
    """Test cases for ModelFSMTransitionCondition instantiation."""

    def test_model_instantiation_minimal(self):
        """Test that model can be instantiated with minimal required data."""
        condition = ModelFSMTransitionCondition(
            condition_name="check_valid",
            condition_type="expression",
            expression="status == active",
        )

        assert condition.condition_name == "check_valid"
        assert condition.condition_type == "expression"
        assert condition.expression == "status == active"
        assert condition.required is True  # Default value
        assert condition.error_message is None  # Default value
        assert condition.retry_count is None  # Default value
        assert condition.timeout_ms is None  # Default value

    def test_model_instantiation_full(self):
        """Test model instantiation with all fields populated."""
        condition = ModelFSMTransitionCondition(
            condition_name="validate_input",
            condition_type="custom",
            expression="input.valid == true",
            required=False,
            error_message="Input validation failed",
            retry_count=3,
            timeout_ms=5000,
        )

        assert condition.condition_name == "validate_input"
        assert condition.condition_type == "custom"
        assert condition.expression == "input.valid == true"
        assert condition.required is False
        assert condition.error_message == "Input validation failed"
        assert condition.retry_count == 3
        assert condition.timeout_ms == 5000

    def test_required_field_default_true(self):
        """Test that required field defaults to True."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
        )

        assert condition.required is True

    def test_required_field_explicit_false(self):
        """Test setting required field to False explicitly."""
        condition = ModelFSMTransitionCondition(
            condition_name="optional_check",
            condition_type="expression",
            expression="value > 0",
            required=False,
        )

        assert condition.required is False

    def test_error_message_optional(self):
        """Test that error_message is optional and defaults to None."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
        )

        assert condition.error_message is None

    def test_error_message_provided(self):
        """Test providing a custom error message."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            error_message="Value must be positive",
        )

        assert condition.error_message == "Value must be positive"

    def test_reserved_fields_default_none(self):
        """Test that reserved fields (retry_count, timeout_ms) default to None."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
        )

        assert condition.retry_count is None
        assert condition.timeout_ms is None

    def test_reserved_fields_can_be_set(self):
        """Test that reserved fields can be set (for v1.1+ compatibility)."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            retry_count=5,
            timeout_ms=10000,
        )

        assert condition.retry_count == 5
        assert condition.timeout_ms == 10000


@pytest.mark.unit
class TestModelFSMTransitionConditionValidation:
    """Test validation rules for ModelFSMTransitionCondition."""

    def test_required_fields_validation(self):
        """Test that required fields are properly validated."""
        # Missing all required fields
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMTransitionCondition()
        error_str = str(exc_info.value)
        assert "condition_name" in error_str
        assert "condition_type" in error_str
        assert "expression" in error_str

    def test_missing_condition_name(self):
        """Test that missing condition_name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMTransitionCondition(
                condition_type="expression",
                expression="value > 0",
            )
        assert "condition_name" in str(exc_info.value)

    def test_missing_condition_type(self):
        """Test that missing condition_type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMTransitionCondition(
                condition_name="check",
                expression="value > 0",
            )
        assert "condition_type" in str(exc_info.value)

    def test_missing_expression(self):
        """Test that missing expression raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
            )
        assert "expression" in str(exc_info.value)

    def test_condition_name_type_validation(self):
        """Test that condition_name must be a string."""
        with pytest.raises(ValidationError):
            ModelFSMTransitionCondition(
                condition_name=123,
                condition_type="expression",
                expression="value > 0",
            )

        with pytest.raises(ValidationError):
            ModelFSMTransitionCondition(
                condition_name=None,
                condition_type="expression",
                expression="value > 0",
            )

        with pytest.raises(ValidationError):
            ModelFSMTransitionCondition(
                condition_name=["check"],
                condition_type="expression",
                expression="value > 0",
            )

    def test_condition_type_type_validation(self):
        """Test that condition_type must be a string."""
        with pytest.raises(ValidationError):
            ModelFSMTransitionCondition(
                condition_name="check",
                condition_type=123,
                expression="value > 0",
            )

        with pytest.raises(ValidationError):
            ModelFSMTransitionCondition(
                condition_name="check",
                condition_type=None,
                expression="value > 0",
            )

    def test_expression_type_validation(self):
        """Test that expression must be a string."""
        with pytest.raises(ValidationError):
            ModelFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression=123,
            )

        with pytest.raises(ValidationError):
            ModelFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression=None,
            )

    def test_required_field_type_validation(self):
        """Test that required field accepts proper boolean types."""
        # Valid boolean values
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            required=True,
        )
        assert condition.required is True

        condition2 = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            required=False,
        )
        assert condition2.required is False

        # Test invalid boolean values that Pydantic cannot coerce
        with pytest.raises(ValidationError):
            ModelFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression="value > 0",
                required=["not_a_bool"],
            )

    def test_retry_count_type_validation(self):
        """Test that retry_count must be an integer or None."""
        # Valid integer
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            retry_count=5,
        )
        assert condition.retry_count == 5

        # None is valid
        condition2 = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            retry_count=None,
        )
        assert condition2.retry_count is None

        # Invalid type
        with pytest.raises(ValidationError):
            ModelFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression="value > 0",
                retry_count="not_an_int",
            )

    def test_timeout_ms_type_validation(self):
        """Test that timeout_ms must be an integer or None."""
        # Valid integer
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            timeout_ms=5000,
        )
        assert condition.timeout_ms == 5000

        # None is valid
        condition2 = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            timeout_ms=None,
        )
        assert condition2.timeout_ms is None

        # Invalid type
        with pytest.raises(ValidationError):
            ModelFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression="value > 0",
                timeout_ms="not_an_int",
            )


@pytest.mark.unit
class TestModelFSMTransitionConditionValidateInstanceBehavior:
    """Test validate_instance() edge cases for cast operations and whitespace handling.

    These tests verify the runtime behavior of cast operations in validate_instance(),
    specifically testing how Python handles type coercion for length checks and
    string comparisons with various whitespace characters.

    PR #165 Review Context:
    - Verifies runtime behavior of cast operations for length checks
    - Verifies runtime behavior of cast operations for numeric comparisons (token count)
    """

    def test_validate_instance_whitespace_only_condition_name_returns_false(self):
        """Test validate_instance returns False for whitespace-only condition_name.

        Runtime behavior: str.strip() removes whitespace, resulting in empty string
        which is falsy. The check `not x.strip()` catches this.
        """
        condition = ModelFSMTransitionCondition(
            condition_name="   ",
            condition_type="expression",
            expression="value > 0",
            required=False,  # Use False to get False return instead of exception
        )
        assert condition.validate_instance() is False

    def test_validate_instance_tab_only_condition_name_returns_false(self):
        """Test validate_instance returns False for tab-only condition_name.

        Runtime behavior: Tab characters are stripped by str.strip(), resulting
        in an empty string which is falsy.
        """
        condition = ModelFSMTransitionCondition(
            condition_name="\t\t",
            condition_type="expression",
            expression="value > 0",
            required=False,
        )
        assert condition.validate_instance() is False

    def test_validate_instance_newline_only_condition_name_returns_false(self):
        """Test validate_instance returns False for newline-only condition_name.

        Runtime behavior: Newline characters are stripped by str.strip(), resulting
        in an empty string which is falsy.
        """
        condition = ModelFSMTransitionCondition(
            condition_name="\n\n",
            condition_type="expression",
            expression="value > 0",
            required=False,
        )
        assert condition.validate_instance() is False

    def test_validate_instance_whitespace_only_condition_type_returns_false(self):
        """Test validate_instance returns False for whitespace-only condition_type."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="   ",
            expression="value > 0",
            required=False,
        )
        assert condition.validate_instance() is False

    def test_validate_instance_tab_only_condition_type_returns_false(self):
        """Test validate_instance returns False for tab-only condition_type."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="\t\t",
            expression="value > 0",
            required=False,
        )
        assert condition.validate_instance() is False

    def test_validate_instance_newline_only_condition_type_returns_false(self):
        """Test validate_instance returns False for newline-only condition_type."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="\n\n",
            expression="value > 0",
            required=False,
        )
        assert condition.validate_instance() is False

    def test_validate_instance_whitespace_only_condition_name_raises_when_required(
        self,
    ):
        """Test validate_instance raises ModelOnexError for whitespace-only name when required=True."""
        condition = ModelFSMTransitionCondition(
            condition_name="   ",
            condition_type="expression",
            expression="value > 0",
            required=True,
        )
        with pytest.raises(ModelOnexError) as exc_info:
            condition.validate_instance()
        assert "condition_name cannot be empty" in str(exc_info.value)

    def test_validate_instance_whitespace_only_condition_type_raises_when_required(
        self,
    ):
        """Test validate_instance raises ModelOnexError for whitespace-only type when required=True."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="   ",
            expression="value > 0",
            required=True,
        )
        with pytest.raises(ModelOnexError) as exc_info:
            condition.validate_instance()
        assert "condition_type cannot be empty" in str(exc_info.value)

    def test_validate_instance_expression_with_multiple_spaces_between_tokens(self):
        """Test expression with multiple spaces between tokens.

        Runtime behavior: str.split() without args splits on any whitespace and
        removes empty strings from result. So "a  ==  b" still produces
        ["a", "==", "b"] (3 tokens).
        """
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value    ==    expected",  # Multiple spaces
        )
        # Should still be valid - split() handles multiple spaces correctly
        assert condition.validate_instance() is True

    def test_validate_instance_expression_with_tabs_between_tokens(self):
        """Test expression with tab characters between tokens.

        Runtime behavior: str.split() treats tabs as whitespace separators,
        so "a\\t==\\tb" produces ["a", "==", "b"] (3 tokens).
        """
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value\t==\texpected",  # Tab separated
        )
        # Should still be valid - split() handles tabs correctly
        assert condition.validate_instance() is True

    def test_validate_instance_expression_with_mixed_whitespace_between_tokens(self):
        """Test expression with mixed whitespace between tokens.

        Runtime behavior: str.split() handles all Unicode whitespace characters
        uniformly, splitting on any of them.
        """
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value \t\n ==  \t expected",  # Mixed whitespace
        )
        # Should still be valid - split() handles mixed whitespace correctly
        assert condition.validate_instance() is True

    def test_validate_instance_expression_with_leading_trailing_whitespace(self):
        """Test expression with leading/trailing whitespace.

        Runtime behavior: str.split() without args ignores leading/trailing
        whitespace, so "  a == b  " produces ["a", "==", "b"] (3 tokens).
        """
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="  value == expected  ",  # Leading/trailing spaces
        )
        # Should still be valid
        assert condition.validate_instance() is True

    def test_validate_instance_len_tokens_comparison_2_tokens(self):
        """Test len(tokens) != 3 comparison with 2 tokens.

        Runtime behavior: len() returns int, comparison with != 3 is
        straightforward integer comparison. 2 != 3 is True.
        """
        # Cannot test directly due to model_validator catching this first
        # But we can use model_construct to bypass it
        condition = ModelFSMTransitionCondition.model_construct(
            condition_name="check",
            condition_type="expression",
            expression="value ==",  # Only 2 tokens
            required=False,
            error_message=None,
            retry_count=None,
            timeout_ms=None,
        )
        assert condition.validate_instance() is False

    def test_validate_instance_len_tokens_comparison_4_tokens(self):
        """Test len(tokens) != 3 comparison with 4 tokens.

        Runtime behavior: len() returns int, comparison with != 3 is
        straightforward integer comparison. 4 != 3 is True.
        """
        # Cannot test directly due to model_validator catching this first
        # But we can use model_construct to bypass it
        condition = ModelFSMTransitionCondition.model_construct(
            condition_name="check",
            condition_type="expression",
            expression="value == expected extra",  # 4 tokens
            required=False,
            error_message=None,
            retry_count=None,
            timeout_ms=None,
        )
        assert condition.validate_instance() is False

    def test_validate_instance_len_tokens_comparison_raises_when_required(self):
        """Test validate_instance raises ModelOnexError for wrong token count when required=True."""
        # Use model_construct to bypass the model_validator
        condition = ModelFSMTransitionCondition.model_construct(
            condition_name="check",
            condition_type="expression",
            expression="value == expected extra",  # 4 tokens
            required=True,
            error_message=None,
            retry_count=None,
            timeout_ms=None,
        )
        with pytest.raises(ModelOnexError) as exc_info:
            condition.validate_instance()
        assert "Expression must have exactly 3 tokens" in str(exc_info.value)
        assert "got 4" in str(exc_info.value)

    def test_validate_instance_empty_condition_name_returns_false(self):
        """Test validate_instance returns False for empty condition_name when required=False.

        Runtime behavior: Empty string "" is falsy in Python. The check
        `if not self.condition_name` catches this before strip() is called.
        """
        condition = ModelFSMTransitionCondition(
            condition_name="",
            condition_type="expression",
            expression="value > 0",
            required=False,
        )
        assert condition.validate_instance() is False

    def test_validate_instance_empty_condition_type_returns_false(self):
        """Test validate_instance returns False for empty condition_type when required=False."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="",
            expression="value > 0",
            required=False,
        )
        assert condition.validate_instance() is False

    def test_validate_instance_mixed_whitespace_condition_name_returns_false(self):
        """Test validate_instance returns False with mixed whitespace characters."""
        condition = ModelFSMTransitionCondition(
            condition_name=" \t\n\r ",
            condition_type="expression",
            expression="value > 0",
            required=False,
        )
        assert condition.validate_instance() is False

    def test_validate_instance_valid_name_surrounded_by_whitespace_passes(self):
        """Test validate_instance passes when valid content is surrounded by whitespace.

        Runtime behavior: str.strip() removes leading/trailing whitespace but
        leaves the middle content intact. Since "valid" is not empty after
        stripping, validate_instance() returns True.
        """
        condition = ModelFSMTransitionCondition(
            condition_name="  valid  ",
            condition_type="\texpression\t",
            expression="value > 0",
        )
        assert condition.validate_instance() is True


@pytest.mark.unit
class TestModelFSMTransitionConditionProtocols:
    """Test protocol implementations for ModelFSMTransitionCondition."""

    def test_execute_protocol_basic(self):
        """Test execute protocol method."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
        )

        # Basic execution should succeed
        result = condition.execute()
        assert result is True

    def test_execute_protocol_with_updates(self):
        """Test execute protocol ignores kwargs (model is frozen).

        Note: Since models are now frozen (immutable), execute() cannot
        modify the model. It returns True but does not mutate fields.
        """
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            error_message="Original message",
        )

        # Execute with updates - model is frozen, so no mutation occurs
        result = condition.execute(error_message="Updated message")
        assert result is True
        # Model is frozen, so error_message should NOT be updated
        assert condition.error_message == "Original message"

    def test_execute_protocol_invalid_field(self):
        """Test execute protocol with invalid field updates."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
        )

        # Execute with non-existent field should still succeed
        result = condition.execute(nonexistent_field="value")
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        condition = ModelFSMTransitionCondition(
            condition_name="validate_input",
            condition_type="custom",
            expression="input.valid == true",
            required=False,
            error_message="Validation failed",
            retry_count=3,
            timeout_ms=5000,
        )

        serialized = condition.serialize()

        assert isinstance(serialized, dict)
        assert serialized["condition_name"] == "validate_input"
        assert serialized["condition_type"] == "custom"
        assert serialized["expression"] == "input.valid == true"
        assert serialized["required"] is False
        assert serialized["error_message"] == "Validation failed"
        assert serialized["retry_count"] == 3
        assert serialized["timeout_ms"] == 5000

    def test_serialize_protocol_minimal(self):
        """Test serialize protocol with minimal condition."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
        )

        serialized = condition.serialize()

        assert isinstance(serialized, dict)
        assert serialized["condition_name"] == "check"
        assert serialized["condition_type"] == "expression"
        assert serialized["expression"] == "value > 0"
        assert serialized["required"] is True
        assert "error_message" in serialized
        assert serialized["error_message"] is None

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol method."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
        )

        # Basic validation should succeed
        result = condition.validate_instance()
        assert result is True

    def test_validate_instance_protocol_complex(self):
        """Test validate_instance with complex condition."""
        condition = ModelFSMTransitionCondition(
            condition_name="complex_check",
            condition_type="custom",
            expression="state.data.field == expected_value",
            required=True,
            error_message="Complex validation failed",
            retry_count=3,
            timeout_ms=10000,
        )

        result = condition.validate_instance()
        assert result is True


@pytest.mark.unit
class TestModelFSMTransitionConditionSerialization:
    """Test serialization and deserialization for ModelFSMTransitionCondition."""

    def test_model_dump(self):
        """Test model_dump method."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            required=True,
            error_message="Check failed",
        )

        data = condition.model_dump()

        assert isinstance(data, dict)
        assert data["condition_name"] == "check"
        assert data["condition_type"] == "expression"
        assert data["expression"] == "value > 0"
        assert data["required"] is True
        assert data["error_message"] == "Check failed"

    def test_model_validate(self):
        """Test model_validate method."""
        data = {
            "condition_name": "validated_check",
            "condition_type": "custom",
            "expression": "data.valid == true",
            "required": False,
            "error_message": "Validation error",
            "retry_count": 2,
            "timeout_ms": 3000,
        }

        condition = ModelFSMTransitionCondition.model_validate(data)

        assert condition.condition_name == "validated_check"
        assert condition.condition_type == "custom"
        assert condition.expression == "data.valid == true"
        assert condition.required is False
        assert condition.error_message == "Validation error"
        assert condition.retry_count == 2
        assert condition.timeout_ms == 3000

    def test_model_dump_json(self):
        """Test JSON serialization."""
        condition = ModelFSMTransitionCondition(
            condition_name="json_test",
            condition_type="expression",
            expression="value > 0",
            required=True,
        )

        json_str = condition.model_dump_json()
        assert isinstance(json_str, str)
        assert "json_test" in json_str
        assert "expression" in json_str

    def test_model_validate_json(self):
        """Test JSON deserialization."""
        json_str = '{"condition_name": "from_json", "condition_type": "custom", "expression": "x == y", "required": false}'

        condition = ModelFSMTransitionCondition.model_validate_json(json_str)

        assert condition.condition_name == "from_json"
        assert condition.condition_type == "custom"
        assert condition.expression == "x == y"
        assert condition.required is False

    def test_roundtrip_serialization(self):
        """Test full roundtrip serialization/deserialization."""
        original = ModelFSMTransitionCondition(
            condition_name="roundtrip_test",
            condition_type="expression",
            expression="status == active",
            required=True,
            error_message="Status must be active",
            retry_count=3,
            timeout_ms=5000,
        )

        # Serialize to dict and back
        data = original.model_dump()
        restored = ModelFSMTransitionCondition.model_validate(data)

        assert restored == original

        # Serialize to JSON and back
        json_str = original.model_dump_json()
        restored_from_json = ModelFSMTransitionCondition.model_validate_json(json_str)

        assert restored_from_json == original


@pytest.mark.unit
class TestModelFSMTransitionConditionEdgeCases:
    """Test edge cases for ModelFSMTransitionCondition."""

    def test_empty_string_condition_name(self):
        """Test condition with empty string condition_name."""
        # Empty name should be valid (no min length constraint in task spec)
        condition = ModelFSMTransitionCondition(
            condition_name="",
            condition_type="expression",
            expression="value > 0",
        )
        assert condition.condition_name == ""

    def test_empty_string_condition_type(self):
        """Test condition with empty string condition_type."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="",
            expression="value > 0",
        )
        assert condition.condition_type == ""

    def test_empty_string_expression(self):
        """Test condition with empty string expression raises ModelOnexError.

        Note: Expression validation now requires exactly 3 tokens.
        Empty string has 0 tokens, so it fails validation.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            ModelFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression="",
            )
        assert "Expression must have exactly 3 tokens" in str(exc_info.value)
        assert "got 0 tokens" in str(exc_info.value)

    def test_invalid_operator_raises_error(self):
        """Test that invalid operators in expression raise ModelOnexError.

        Only the following operators are valid:
        ==, !=, <, >, <=, >=, in, not_in, contains, matches,
        equals, not_equals, greater_than, less_than,
        greater_than_or_equal, less_than_or_equal
        """
        invalid_operators = ["INVALID", "is", "===", "!==", "and", "or"]
        for invalid_op in invalid_operators:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelFSMTransitionCondition(
                    condition_name="check",
                    condition_type="expression",
                    expression=f"value {invalid_op} expected",
                )
            error_msg = str(exc_info.value)
            assert "Invalid operator" in error_msg
            assert invalid_op in error_msg

    def test_valid_operators(self):
        """Test that all valid operators are accepted.

        Valid operators:
        - Symbol-based: ==, !=, <, >, <=, >=
        - Word-based: in, not_in, contains, matches
        - Word-based equality: equals, not_equals
        - Word-based comparison: greater_than, less_than,
          greater_than_or_equal, less_than_or_equal
        """
        valid_operators = [
            "==",
            "!=",
            "<",
            ">",
            "<=",
            ">=",
            "in",
            "not_in",
            "contains",
            "matches",
            # Word-based equality operators
            "equals",
            "not_equals",
            # Word-based comparison operators
            "greater_than",
            "less_than",
            "greater_than_or_equal",
            "less_than_or_equal",
        ]
        for valid_op in valid_operators:
            condition = ModelFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression=f"value {valid_op} expected",
            )
            assert condition.expression == f"value {valid_op} expected"

    def test_very_long_expression(self):
        """Test condition with very long expression."""
        long_expr = "field_" + "x" * 10000 + " == value"
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression=long_expr,
        )
        assert len(condition.expression) > 10000

    def test_condition_name_with_special_characters(self):
        """Test condition names with special characters."""
        special_names = [
            "condition-with-dashes",
            "condition_with_underscores",
            "condition.with.dots",
            "condition:with:colons",
            "condition/with/slashes",
            "condition with spaces",
            "condition_francais",
            "condition_123",
        ]

        for name in special_names:
            condition = ModelFSMTransitionCondition(
                condition_name=name,
                condition_type="expression",
                expression="value > 0",
            )
            assert condition.condition_name == name

    def test_expression_with_operators(self):
        """Test expressions with various operators."""
        expressions = [
            "value > 0",
            "value >= 0",
            "value < 100",
            "value <= 100",
            "value == expected",
            "value != invalid",
            "status == active",
            "count >= threshold",
        ]

        for expr in expressions:
            condition = ModelFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression=expr,
            )
            assert condition.expression == expr

    def test_condition_type_variations(self):
        """Test various condition types."""
        condition_types = [
            "expression",
            "custom",
            "validation",
            "state",
            "processing",
            "guard",
            "precondition",
            "postcondition",
        ]

        for ctype in condition_types:
            condition = ModelFSMTransitionCondition(
                condition_name="check",
                condition_type=ctype,
                expression="value > 0",
            )
            assert condition.condition_type == ctype

    def test_error_message_with_special_characters(self):
        """Test error messages with special characters."""
        special_messages = [
            "Error: Value must be > 0",
            "Failed validation for 'field_name'",
            'Expected "active" but got "inactive"',
            "Condition failed! Please retry.",
            "Error message with newline\nand another line",
        ]

        for msg in special_messages:
            condition = ModelFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression="value > 0",
                error_message=msg,
            )
            assert condition.error_message == msg

    def test_retry_count_zero(self):
        """Test retry_count with zero value (allowed by ge=0 constraint)."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            retry_count=0,
        )
        assert condition.retry_count == 0

    def test_timeout_ms_zero(self):
        """Test timeout_ms with zero value is rejected (gt=0 constraint).

        A timeout of 0ms doesn't make practical sense, so the constraint
        requires timeout_ms > 0 when specified.
        """
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression="value > 0",
                timeout_ms=0,
            )
        assert "greater than 0" in str(exc_info.value)

    def test_large_retry_count(self):
        """Test with large retry count value."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            retry_count=1000000,
        )
        assert condition.retry_count == 1000000

    def test_large_timeout_ms(self):
        """Test with large timeout_ms value."""
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            timeout_ms=86400000,  # 24 hours in ms
        )
        assert condition.timeout_ms == 86400000

    def test_model_equality(self):
        """Test model equality comparison."""
        condition1 = ModelFSMTransitionCondition(
            condition_name="equal",
            condition_type="expression",
            expression="value > 0",
            required=True,
        )
        condition2 = ModelFSMTransitionCondition(
            condition_name="equal",
            condition_type="expression",
            expression="value > 0",
            required=True,
        )
        condition3 = ModelFSMTransitionCondition(
            condition_name="different",
            condition_type="expression",
            expression="value > 0",
            required=True,
        )

        assert condition1 == condition2
        assert condition1 != condition3

    def test_validate_assignment_config(self):
        """Test that frozen model prevents assignment.

        Note: Model is now frozen (immutable). Any attempt to assign
        to a field will raise ValidationError with frozen_instance error.
        """
        condition = ModelFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
        )

        # Model is frozen, so assignment should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            condition.error_message = "Updated error"
        assert "frozen" in str(exc_info.value).lower()

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored per config."""
        data = {
            "condition_name": "check",
            "condition_type": "expression",
            "expression": "value > 0",
            "extra_field": "should_be_ignored",
            "another_extra": 123,
        }

        condition = ModelFSMTransitionCondition.model_validate(data)
        assert condition.condition_name == "check"
        assert not hasattr(condition, "extra_field")
        assert not hasattr(condition, "another_extra")

    def test_negative_retry_count(self):
        """Test that negative retry_count raises ValidationError.

        Note: retry_count has ge=0 constraint, so negative values are rejected.
        """
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression="value > 0",
                retry_count=-1,
            )
        assert "retry_count" in str(exc_info.value)

    def test_negative_timeout_ms(self):
        """Test that negative timeout_ms raises ValidationError.

        Note: timeout_ms has ge=0 constraint, so negative values are rejected.
        """
        with pytest.raises(ValidationError) as exc_info:
            ModelFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression="value > 0",
                timeout_ms=-1000,
            )
        assert "timeout_ms" in str(exc_info.value)


@pytest.mark.unit
class TestModelFSMTransitionConditionImport:
    """Test that the model can be imported from the fsm module."""

    def test_import_from_fsm_module(self):
        """Test importing from the fsm package."""
        from omnibase_core.models.fsm import (
            ModelFSMTransitionCondition as ImportedModel,
        )

        condition = ImportedModel(
            condition_name="import_test",
            condition_type="expression",
            expression="value > 0",
        )

        assert condition.condition_name == "import_test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
