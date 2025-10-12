"""Tests for ModelFieldValidationRules."""

import pytest

from omnibase_core.enums.enum_numeric_type import EnumNumericType
from omnibase_core.models.common.model_numeric_value import ModelNumericValue
from omnibase_core.models.metadata.model_field_validation_rules import (
    ModelFieldValidationRules,
)


class TestModelFieldValidationRulesInstantiation:
    """Tests for ModelFieldValidationRules instantiation."""

    def test_create_default_rules(self):
        """Test creating validation rules with defaults."""
        rules = ModelFieldValidationRules()
        assert rules.validation_pattern is None
        assert rules.min_length is None
        assert rules.max_length is None
        assert rules.min_value is None
        assert rules.max_value is None
        assert rules.allow_empty is True

    def test_create_with_string_validation(self):
        """Test creating rules with string validation."""
        rules = ModelFieldValidationRules(
            validation_pattern=r"^[A-Z]+$",
            min_length=5,
            max_length=10,
        )
        assert rules.validation_pattern == r"^[A-Z]+$"
        assert rules.min_length == 5
        assert rules.max_length == 10

    def test_create_with_numeric_validation(self):
        """Test creating rules with numeric validation."""
        min_val = ModelNumericValue.from_int(0)
        max_val = ModelNumericValue.from_int(100)
        rules = ModelFieldValidationRules(min_value=min_val, max_value=max_val)
        assert rules.min_value == min_val
        assert rules.max_value == max_val

    def test_create_with_allow_empty_false(self):
        """Test creating rules with allow_empty False."""
        rules = ModelFieldValidationRules(allow_empty=False)
        assert rules.allow_empty is False


class TestModelFieldValidationRulesHasValidation:
    """Tests for validation detection methods."""

    def test_has_string_validation_with_pattern(self):
        """Test has_string_validation with pattern."""
        rules = ModelFieldValidationRules(validation_pattern=r"^\d+$")
        assert rules.has_string_validation() is True

    def test_has_string_validation_with_min_length(self):
        """Test has_string_validation with min_length."""
        rules = ModelFieldValidationRules(min_length=5)
        assert rules.has_string_validation() is True

    def test_has_string_validation_with_max_length(self):
        """Test has_string_validation with max_length."""
        rules = ModelFieldValidationRules(max_length=10)
        assert rules.has_string_validation() is True

    def test_has_string_validation_false(self):
        """Test has_string_validation returns False without string rules."""
        rules = ModelFieldValidationRules()
        assert rules.has_string_validation() is False

    def test_has_numeric_validation_with_min(self):
        """Test has_numeric_validation with min_value."""
        min_val = ModelNumericValue.from_int(0)
        rules = ModelFieldValidationRules(min_value=min_val)
        assert rules.has_numeric_validation() is True

    def test_has_numeric_validation_with_max(self):
        """Test has_numeric_validation with max_value."""
        max_val = ModelNumericValue.from_int(100)
        rules = ModelFieldValidationRules(max_value=max_val)
        assert rules.has_numeric_validation() is True

    def test_has_numeric_validation_false(self):
        """Test has_numeric_validation returns False without numeric rules."""
        rules = ModelFieldValidationRules()
        assert rules.has_numeric_validation() is False


class TestModelFieldValidationRulesStringValidation:
    """Tests for string validation."""

    def test_is_valid_string_with_min_length_pass(self):
        """Test is_valid_string passes with valid min_length."""
        rules = ModelFieldValidationRules(min_length=5)
        assert rules.is_valid_string("hello") is True
        assert rules.is_valid_string("hello world") is True

    def test_is_valid_string_with_min_length_fail(self):
        """Test is_valid_string fails with invalid min_length."""
        rules = ModelFieldValidationRules(min_length=5)
        assert rules.is_valid_string("hi") is False

    def test_is_valid_string_with_max_length_pass(self):
        """Test is_valid_string passes with valid max_length."""
        rules = ModelFieldValidationRules(max_length=10)
        assert rules.is_valid_string("hello") is True

    def test_is_valid_string_with_max_length_fail(self):
        """Test is_valid_string fails with invalid max_length."""
        rules = ModelFieldValidationRules(max_length=10)
        assert rules.is_valid_string("this is too long") is False

    def test_is_valid_string_with_pattern_pass(self):
        """Test is_valid_string passes with valid pattern."""
        rules = ModelFieldValidationRules(validation_pattern=r"^[A-Z]+$")
        assert rules.is_valid_string("HELLO") is True
        assert rules.is_valid_string("ABC") is True

    def test_is_valid_string_with_pattern_fail(self):
        """Test is_valid_string fails with invalid pattern."""
        rules = ModelFieldValidationRules(validation_pattern=r"^[A-Z]+$")
        assert rules.is_valid_string("hello") is False
        assert rules.is_valid_string("Hello") is False

    def test_is_valid_string_with_allow_empty_false(self):
        """Test is_valid_string with allow_empty False."""
        rules = ModelFieldValidationRules(allow_empty=False)
        assert rules.is_valid_string("") is False
        assert rules.is_valid_string("text") is True

    def test_is_valid_string_with_allow_empty_true(self):
        """Test is_valid_string with allow_empty True."""
        rules = ModelFieldValidationRules(allow_empty=True)
        assert rules.is_valid_string("") is True

    def test_is_valid_string_with_invalid_pattern(self):
        """Test is_valid_string with invalid regex pattern."""
        rules = ModelFieldValidationRules(validation_pattern=r"[invalid(")
        # Should return False for invalid regex
        assert rules.is_valid_string("test") is False

    def test_is_valid_string_combined_rules(self):
        """Test is_valid_string with combined rules."""
        rules = ModelFieldValidationRules(
            min_length=3,
            max_length=10,
            validation_pattern=r"^[A-Za-z]+$",
        )
        assert rules.is_valid_string("hello") is True
        assert rules.is_valid_string("hi") is False  # Too short
        assert rules.is_valid_string("thisisverylongtext") is False  # Too long
        assert rules.is_valid_string("test123") is False  # Pattern mismatch


class TestModelFieldValidationRulesNumericValidation:
    """Tests for numeric validation."""

    def test_is_valid_numeric_with_min_value_pass(self):
        """Test is_valid_numeric passes with valid min_value."""
        min_val = ModelNumericValue.from_int(0)
        rules = ModelFieldValidationRules(min_value=min_val)
        test_val = ModelNumericValue.from_int(5)
        assert rules.is_valid_numeric(test_val) is True

    def test_is_valid_numeric_with_min_value_fail(self):
        """Test is_valid_numeric fails with invalid min_value."""
        min_val = ModelNumericValue.from_int(10)
        rules = ModelFieldValidationRules(min_value=min_val)
        test_val = ModelNumericValue.from_int(5)
        assert rules.is_valid_numeric(test_val) is False

    def test_is_valid_numeric_with_max_value_pass(self):
        """Test is_valid_numeric passes with valid max_value."""
        max_val = ModelNumericValue.from_int(100)
        rules = ModelFieldValidationRules(max_value=max_val)
        test_val = ModelNumericValue.from_int(50)
        assert rules.is_valid_numeric(test_val) is True

    def test_is_valid_numeric_with_max_value_fail(self):
        """Test is_valid_numeric fails with invalid max_value."""
        max_val = ModelNumericValue.from_int(100)
        rules = ModelFieldValidationRules(max_value=max_val)
        test_val = ModelNumericValue.from_int(150)
        assert rules.is_valid_numeric(test_val) is False

    def test_is_valid_numeric_with_float_values(self):
        """Test is_valid_numeric with float values."""
        min_val = ModelNumericValue.from_float(0.5)
        max_val = ModelNumericValue.from_float(10.5)
        rules = ModelFieldValidationRules(min_value=min_val, max_value=max_val)
        test_val = ModelNumericValue.from_float(5.5)
        assert rules.is_valid_numeric(test_val) is True

    def test_is_valid_numeric_boundary_min(self):
        """Test is_valid_numeric at minimum boundary."""
        min_val = ModelNumericValue.from_int(10)
        rules = ModelFieldValidationRules(min_value=min_val)
        test_val = ModelNumericValue.from_int(10)
        assert rules.is_valid_numeric(test_val) is True

    def test_is_valid_numeric_boundary_max(self):
        """Test is_valid_numeric at maximum boundary."""
        max_val = ModelNumericValue.from_int(100)
        rules = ModelFieldValidationRules(max_value=max_val)
        test_val = ModelNumericValue.from_int(100)
        assert rules.is_valid_numeric(test_val) is True

    def test_is_valid_numeric_combined_rules(self):
        """Test is_valid_numeric with combined min and max."""
        min_val = ModelNumericValue.from_int(10)
        max_val = ModelNumericValue.from_int(100)
        rules = ModelFieldValidationRules(min_value=min_val, max_value=max_val)
        assert rules.is_valid_numeric(ModelNumericValue.from_int(50)) is True
        assert rules.is_valid_numeric(ModelNumericValue.from_int(5)) is False
        assert rules.is_valid_numeric(ModelNumericValue.from_int(150)) is False


class TestModelFieldValidationRulesSetters:
    """Tests for setter methods."""

    def test_set_min_value(self):
        """Test set_min_value method."""
        rules = ModelFieldValidationRules()
        min_val = ModelNumericValue.from_int(10)
        rules.set_min_value(min_val)
        assert rules.min_value == min_val

    def test_set_max_value(self):
        """Test set_max_value method."""
        rules = ModelFieldValidationRules()
        max_val = ModelNumericValue.from_int(100)
        rules.set_max_value(max_val)
        assert rules.max_value == max_val

    def test_set_min_max_values(self):
        """Test setting both min and max values."""
        rules = ModelFieldValidationRules()
        min_val = ModelNumericValue.from_int(0)
        max_val = ModelNumericValue.from_int(100)
        rules.set_min_value(min_val)
        rules.set_max_value(max_val)
        assert rules.min_value == min_val
        assert rules.max_value == max_val


class TestModelFieldValidationRulesGetters:
    """Tests for getter methods."""

    def test_get_min_value_with_value(self):
        """Test get_min_value returns value."""
        min_val = ModelNumericValue.from_int(10)
        rules = ModelFieldValidationRules(min_value=min_val)
        assert rules.get_min_value() == min_val

    def test_get_min_value_without_value(self):
        """Test get_min_value returns None."""
        rules = ModelFieldValidationRules()
        assert rules.get_min_value() is None

    def test_get_max_value_with_value(self):
        """Test get_max_value returns value."""
        max_val = ModelNumericValue.from_int(100)
        rules = ModelFieldValidationRules(max_value=max_val)
        assert rules.get_max_value() == max_val

    def test_get_max_value_without_value(self):
        """Test get_max_value returns None."""
        rules = ModelFieldValidationRules()
        assert rules.get_max_value() is None


class TestModelFieldValidationRulesProtocols:
    """Tests for protocol implementations."""

    def test_get_metadata(self):
        """Test get_metadata method."""
        rules = ModelFieldValidationRules()
        metadata = rules.get_metadata()
        assert isinstance(metadata, dict)

    def test_set_metadata(self):
        """Test set_metadata method."""
        rules = ModelFieldValidationRules()
        result = rules.set_metadata({"allow_empty": False})
        assert result is True
        assert rules.allow_empty is False

    def test_serialize(self):
        """Test serialize method."""
        rules = ModelFieldValidationRules(min_length=5, max_length=10)
        data = rules.serialize()
        assert isinstance(data, dict)
        assert "min_length" in data
        assert "max_length" in data

    def test_validate_instance(self):
        """Test validate_instance method."""
        rules = ModelFieldValidationRules()
        assert rules.validate_instance() is True


class TestModelFieldValidationRulesEdgeCases:
    """Tests for edge cases."""

    def test_zero_min_length(self):
        """Test with zero min_length."""
        rules = ModelFieldValidationRules(min_length=0)
        assert rules.is_valid_string("") is True
        assert rules.is_valid_string("text") is True

    def test_zero_max_length(self):
        """Test with zero max_length."""
        rules = ModelFieldValidationRules(max_length=0)
        assert rules.is_valid_string("") is True
        assert rules.is_valid_string("a") is False

    def test_negative_numeric_values(self):
        """Test with negative numeric values."""
        min_val = ModelNumericValue.from_int(-100)
        max_val = ModelNumericValue.from_int(-10)
        rules = ModelFieldValidationRules(min_value=min_val, max_value=max_val)
        test_val = ModelNumericValue.from_int(-50)
        assert rules.is_valid_numeric(test_val) is True

    def test_very_large_numeric_values(self):
        """Test with very large numeric values."""
        min_val = ModelNumericValue.from_int(1000000)
        max_val = ModelNumericValue.from_int(10000000)
        rules = ModelFieldValidationRules(min_value=min_val, max_value=max_val)
        test_val = ModelNumericValue.from_int(5000000)
        assert rules.is_valid_numeric(test_val) is True

    def test_unicode_string_validation(self):
        """Test string validation with unicode characters."""
        rules = ModelFieldValidationRules(min_length=3, max_length=10)
        assert rules.is_valid_string("こんにちは") is True

    def test_empty_pattern(self):
        """Test with empty pattern string."""
        rules = ModelFieldValidationRules(validation_pattern="")
        # Empty pattern should match any string
        assert rules.is_valid_string("anything") is True

    def test_complex_regex_pattern(self):
        """Test with complex regex pattern."""
        # Email-like pattern
        rules = ModelFieldValidationRules(
            validation_pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        )
        assert rules.is_valid_string("test@example.com") is True
        assert rules.is_valid_string("invalid-email") is False


class TestModelFieldValidationRulesSerialization:
    """Tests for serialization."""

    def test_model_dump_with_all_fields(self):
        """Test model_dump with all fields populated."""
        min_val = ModelNumericValue.from_int(0)
        max_val = ModelNumericValue.from_int(100)
        rules = ModelFieldValidationRules(
            validation_pattern=r"^\d+$",
            min_length=1,
            max_length=10,
            min_value=min_val,
            max_value=max_val,
            allow_empty=False,
        )
        data = rules.model_dump()
        assert data["validation_pattern"] == r"^\d+$"
        assert data["min_length"] == 1
        assert data["max_length"] == 10
        assert data["allow_empty"] is False

    def test_model_dump_exclude_none(self):
        """Test model_dump with exclude_none."""
        rules = ModelFieldValidationRules(min_length=5)
        data = rules.model_dump(exclude_none=True)
        assert "min_length" in data
        assert "validation_pattern" not in data
        assert "max_length" not in data


class TestModelFieldValidationRulesErrorBranches:
    """Tests for error handling branches in ModelFieldValidationRules."""

    def test_get_metadata_with_none_values(self):
        """Test get_metadata when field values are None (line 149 branch)."""
        # Create rules with all None optional fields
        rules = ModelFieldValidationRules()
        metadata = rules.get_metadata()
        # Should not include None values in metadata
        assert isinstance(metadata, dict)
        # None fields should not be in metadata
        for key in ["validation_pattern", "min_length", "max_length"]:
            if key in metadata:
                assert metadata[key] is not None

    def test_get_metadata_without_common_fields(self):
        """Test get_metadata when model doesn't have common metadata fields."""
        rules = ModelFieldValidationRules(min_length=5)
        metadata = rules.get_metadata()
        # Should handle missing common fields gracefully
        assert isinstance(metadata, dict)
        # Common fields like 'name', 'version', 'tags' don't exist on this model

    def test_set_metadata_with_invalid_keys(self):
        """Test set_metadata with keys that don't exist (line 159->158 branch)."""
        rules = ModelFieldValidationRules()
        # Try to set fields including non-existent ones
        result = rules.set_metadata(
            {
                "allow_empty": False,
                "non_existent_field": "invalid",  # Should be ignored
                "another_invalid": 123,  # Should be ignored
            }
        )
        assert result is True
        assert rules.allow_empty is False
        # Non-existent fields should not cause errors

    def test_set_metadata_with_validation_error(self):
        """Test set_metadata exception handling (lines 162-163 branch)."""
        from omnibase_core.errors.error_codes import EnumCoreErrorCode
        from omnibase_core.errors.model_onex_error import ModelOnexError

        rules = ModelFieldValidationRules()
        # Try to set min_length to invalid type
        with pytest.raises(ModelOnexError) as exc_info:
            rules.set_metadata({"min_length": "not-an-integer"})

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Operation failed" in str(exc_info.value.message)

    def test_set_metadata_with_type_conversion_error(self):
        """Test set_metadata with value that causes type error."""
        from omnibase_core.errors.model_onex_error import ModelOnexError

        rules = ModelFieldValidationRules()
        # Try to set max_length to a value that fails validation
        with pytest.raises(ModelOnexError) as exc_info:
            rules.set_metadata({"max_length": []})  # List instead of int

        assert exc_info.value.error_code
        assert "Operation failed" in str(exc_info.value.message)

    def test_set_metadata_with_invalid_numeric_value(self):
        """Test set_metadata with invalid ModelNumericValue."""
        from omnibase_core.errors.model_onex_error import ModelOnexError

        rules = ModelFieldValidationRules()
        # Try to set min_value to wrong type
        with pytest.raises(ModelOnexError) as exc_info:
            rules.set_metadata({"min_value": "not-a-numeric-value"})

        assert exc_info.value.error_code
        assert "Operation failed" in str(exc_info.value.message)
