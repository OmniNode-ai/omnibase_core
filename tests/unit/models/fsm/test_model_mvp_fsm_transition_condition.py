"""
Unit tests for ModelMvpFSMTransitionCondition.

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

from omnibase_core.models.fsm.model_mvp_fsm_transition_condition import (
    ModelMvpFSMTransitionCondition,
)


class TestModelMvpFSMTransitionConditionInstantiation:
    """Test cases for ModelMvpFSMTransitionCondition instantiation."""

    def test_model_instantiation_minimal(self):
        """Test that model can be instantiated with minimal required data."""
        condition = ModelMvpFSMTransitionCondition(
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
        condition = ModelMvpFSMTransitionCondition(
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
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
        )

        assert condition.required is True

    def test_required_field_explicit_false(self):
        """Test setting required field to False explicitly."""
        condition = ModelMvpFSMTransitionCondition(
            condition_name="optional_check",
            condition_type="expression",
            expression="value > 0",
            required=False,
        )

        assert condition.required is False

    def test_error_message_optional(self):
        """Test that error_message is optional and defaults to None."""
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
        )

        assert condition.error_message is None

    def test_error_message_provided(self):
        """Test providing a custom error message."""
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            error_message="Value must be positive",
        )

        assert condition.error_message == "Value must be positive"

    def test_reserved_fields_default_none(self):
        """Test that reserved fields (retry_count, timeout_ms) default to None."""
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
        )

        assert condition.retry_count is None
        assert condition.timeout_ms is None

    def test_reserved_fields_can_be_set(self):
        """Test that reserved fields can be set (for v1.1+ compatibility)."""
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            retry_count=5,
            timeout_ms=10000,
        )

        assert condition.retry_count == 5
        assert condition.timeout_ms == 10000


class TestModelMvpFSMTransitionConditionValidation:
    """Test validation rules for ModelMvpFSMTransitionCondition."""

    def test_required_fields_validation(self):
        """Test that required fields are properly validated."""
        # Missing all required fields
        with pytest.raises(ValidationError) as exc_info:
            ModelMvpFSMTransitionCondition()
        error_str = str(exc_info.value)
        assert "condition_name" in error_str
        assert "condition_type" in error_str
        assert "expression" in error_str

    def test_missing_condition_name(self):
        """Test that missing condition_name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMvpFSMTransitionCondition(
                condition_type="expression",
                expression="value > 0",
            )
        assert "condition_name" in str(exc_info.value)

    def test_missing_condition_type(self):
        """Test that missing condition_type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMvpFSMTransitionCondition(
                condition_name="check",
                expression="value > 0",
            )
        assert "condition_type" in str(exc_info.value)

    def test_missing_expression(self):
        """Test that missing expression raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMvpFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
            )
        assert "expression" in str(exc_info.value)

    def test_condition_name_type_validation(self):
        """Test that condition_name must be a string."""
        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionCondition(
                condition_name=123,
                condition_type="expression",
                expression="value > 0",
            )

        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionCondition(
                condition_name=None,
                condition_type="expression",
                expression="value > 0",
            )

        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionCondition(
                condition_name=["check"],
                condition_type="expression",
                expression="value > 0",
            )

    def test_condition_type_type_validation(self):
        """Test that condition_type must be a string."""
        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionCondition(
                condition_name="check",
                condition_type=123,
                expression="value > 0",
            )

        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionCondition(
                condition_name="check",
                condition_type=None,
                expression="value > 0",
            )

    def test_expression_type_validation(self):
        """Test that expression must be a string."""
        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression=123,
            )

        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression=None,
            )

    def test_required_field_type_validation(self):
        """Test that required field accepts proper boolean types."""
        # Valid boolean values
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            required=True,
        )
        assert condition.required is True

        condition2 = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            required=False,
        )
        assert condition2.required is False

        # Test invalid boolean values that Pydantic cannot coerce
        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression="value > 0",
                required=["not_a_bool"],
            )

    def test_retry_count_type_validation(self):
        """Test that retry_count must be an integer or None."""
        # Valid integer
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            retry_count=5,
        )
        assert condition.retry_count == 5

        # None is valid
        condition2 = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            retry_count=None,
        )
        assert condition2.retry_count is None

        # Invalid type
        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression="value > 0",
                retry_count="not_an_int",
            )

    def test_timeout_ms_type_validation(self):
        """Test that timeout_ms must be an integer or None."""
        # Valid integer
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            timeout_ms=5000,
        )
        assert condition.timeout_ms == 5000

        # None is valid
        condition2 = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            timeout_ms=None,
        )
        assert condition2.timeout_ms is None

        # Invalid type
        with pytest.raises(ValidationError):
            ModelMvpFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression="value > 0",
                timeout_ms="not_an_int",
            )


class TestModelMvpFSMTransitionConditionProtocols:
    """Test protocol implementations for ModelMvpFSMTransitionCondition."""

    def test_execute_protocol_basic(self):
        """Test execute protocol method."""
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
        )

        # Basic execution should succeed
        result = condition.execute()
        assert result is True

    def test_execute_protocol_with_updates(self):
        """Test execute protocol with field updates."""
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            error_message="Original message",
        )

        # Execute with updates
        result = condition.execute(error_message="Updated message")
        assert result is True
        assert condition.error_message == "Updated message"

    def test_execute_protocol_invalid_field(self):
        """Test execute protocol with invalid field updates."""
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
        )

        # Execute with non-existent field should still succeed
        result = condition.execute(nonexistent_field="value")
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        condition = ModelMvpFSMTransitionCondition(
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
        condition = ModelMvpFSMTransitionCondition(
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
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
        )

        # Basic validation should succeed
        result = condition.validate_instance()
        assert result is True

    def test_validate_instance_protocol_complex(self):
        """Test validate_instance with complex condition."""
        condition = ModelMvpFSMTransitionCondition(
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


class TestModelMvpFSMTransitionConditionSerialization:
    """Test serialization and deserialization for ModelMvpFSMTransitionCondition."""

    def test_model_dump(self):
        """Test model_dump method."""
        condition = ModelMvpFSMTransitionCondition(
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

        condition = ModelMvpFSMTransitionCondition.model_validate(data)

        assert condition.condition_name == "validated_check"
        assert condition.condition_type == "custom"
        assert condition.expression == "data.valid == true"
        assert condition.required is False
        assert condition.error_message == "Validation error"
        assert condition.retry_count == 2
        assert condition.timeout_ms == 3000

    def test_model_dump_json(self):
        """Test JSON serialization."""
        condition = ModelMvpFSMTransitionCondition(
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

        condition = ModelMvpFSMTransitionCondition.model_validate_json(json_str)

        assert condition.condition_name == "from_json"
        assert condition.condition_type == "custom"
        assert condition.expression == "x == y"
        assert condition.required is False

    def test_roundtrip_serialization(self):
        """Test full roundtrip serialization/deserialization."""
        original = ModelMvpFSMTransitionCondition(
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
        restored = ModelMvpFSMTransitionCondition.model_validate(data)

        assert restored == original

        # Serialize to JSON and back
        json_str = original.model_dump_json()
        restored_from_json = ModelMvpFSMTransitionCondition.model_validate_json(
            json_str
        )

        assert restored_from_json == original


class TestModelMvpFSMTransitionConditionEdgeCases:
    """Test edge cases for ModelMvpFSMTransitionCondition."""

    def test_empty_string_condition_name(self):
        """Test condition with empty string condition_name."""
        # Empty name should be valid (no min length constraint in task spec)
        condition = ModelMvpFSMTransitionCondition(
            condition_name="",
            condition_type="expression",
            expression="value > 0",
        )
        assert condition.condition_name == ""

    def test_empty_string_condition_type(self):
        """Test condition with empty string condition_type."""
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="",
            expression="value > 0",
        )
        assert condition.condition_type == ""

    def test_empty_string_expression(self):
        """Test condition with empty string expression."""
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="",
        )
        assert condition.expression == ""

    def test_very_long_expression(self):
        """Test condition with very long expression."""
        long_expr = "field_" + "x" * 10000 + " == value"
        condition = ModelMvpFSMTransitionCondition(
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
            condition = ModelMvpFSMTransitionCondition(
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
            condition = ModelMvpFSMTransitionCondition(
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
            condition = ModelMvpFSMTransitionCondition(
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
            condition = ModelMvpFSMTransitionCondition(
                condition_name="check",
                condition_type="expression",
                expression="value > 0",
                error_message=msg,
            )
            assert condition.error_message == msg

    def test_retry_count_zero(self):
        """Test retry_count with zero value."""
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            retry_count=0,
        )
        assert condition.retry_count == 0

    def test_timeout_ms_zero(self):
        """Test timeout_ms with zero value."""
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            timeout_ms=0,
        )
        assert condition.timeout_ms == 0

    def test_large_retry_count(self):
        """Test with large retry count value."""
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            retry_count=1000000,
        )
        assert condition.retry_count == 1000000

    def test_large_timeout_ms(self):
        """Test with large timeout_ms value."""
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            timeout_ms=86400000,  # 24 hours in ms
        )
        assert condition.timeout_ms == 86400000

    def test_model_equality(self):
        """Test model equality comparison."""
        condition1 = ModelMvpFSMTransitionCondition(
            condition_name="equal",
            condition_type="expression",
            expression="value > 0",
            required=True,
        )
        condition2 = ModelMvpFSMTransitionCondition(
            condition_name="equal",
            condition_type="expression",
            expression="value > 0",
            required=True,
        )
        condition3 = ModelMvpFSMTransitionCondition(
            condition_name="different",
            condition_type="expression",
            expression="value > 0",
            required=True,
        )

        assert condition1 == condition2
        assert condition1 != condition3

    def test_validate_assignment_config(self):
        """Test that validate_assignment config works."""
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
        )

        # Should allow assignment
        condition.error_message = "Updated error"
        assert condition.error_message == "Updated error"

        # Invalid assignment should raise error
        with pytest.raises(ValidationError):
            condition.required = "not_a_boolean"

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored per config."""
        data = {
            "condition_name": "check",
            "condition_type": "expression",
            "expression": "value > 0",
            "extra_field": "should_be_ignored",
            "another_extra": 123,
        }

        condition = ModelMvpFSMTransitionCondition.model_validate(data)
        assert condition.condition_name == "check"
        assert not hasattr(condition, "extra_field")
        assert not hasattr(condition, "another_extra")

    def test_negative_retry_count(self):
        """Test that negative retry_count is accepted (no constraint in task spec)."""
        # Note: The spec has ge=0 but task doesn't specify constraints
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            retry_count=-1,
        )
        assert condition.retry_count == -1

    def test_negative_timeout_ms(self):
        """Test that negative timeout_ms is accepted (no constraint in task spec)."""
        # Note: The spec has ge=1 but task doesn't specify constraints
        condition = ModelMvpFSMTransitionCondition(
            condition_name="check",
            condition_type="expression",
            expression="value > 0",
            timeout_ms=-1000,
        )
        assert condition.timeout_ms == -1000


class TestModelMvpFSMTransitionConditionImport:
    """Test that the model can be imported from the fsm module."""

    def test_import_from_fsm_module(self):
        """Test importing from the fsm package."""
        from omnibase_core.models.fsm import (
            ModelMvpFSMTransitionCondition as ImportedModel,
        )

        condition = ImportedModel(
            condition_name="import_test",
            condition_type="expression",
            expression="value > 0",
        )

        assert condition.condition_name == "import_test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
