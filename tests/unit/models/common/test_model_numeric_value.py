# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelNumericValue."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_numeric_type import EnumNumericType
from omnibase_core.models.common.model_numeric_value import ModelNumericValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError as OnexError


@pytest.mark.unit
class TestModelNumericValueInstantiation:
    """Tests for ModelNumericValue instantiation."""

    def test_create_from_int(self):
        """Test creating numeric value from integer."""
        value = ModelNumericValue.from_int(42)
        assert value.value == 42.0
        assert value.value_type == EnumNumericType.INTEGER
        assert value.is_validated is True

    def test_create_from_float(self):
        """Test creating numeric value from float."""
        value = ModelNumericValue.from_float(3.14)
        assert value.value == 3.14
        assert value.value_type == EnumNumericType.FLOAT
        assert value.is_validated is True

    def test_create_from_numeric_int(self):
        """Test from_numeric with integer."""
        value = ModelNumericValue.from_numeric(42)
        assert value.value_type == EnumNumericType.INTEGER
        assert value.value == 42.0

    def test_create_from_numeric_float(self):
        """Test from_numeric with float."""
        value = ModelNumericValue.from_numeric(3.14)
        assert value.value_type == EnumNumericType.FLOAT
        assert value.value == 3.14

    def test_create_with_source(self):
        """Test creating value with source."""
        value = ModelNumericValue.from_int(42, source="test_source")
        assert value.source == "test_source"


@pytest.mark.unit
class TestModelNumericValueValidation:
    """Tests for ModelNumericValue validation."""

    def test_invalid_value_type_string(self):
        """Test that string value raises error."""
        # Pydantic raises ValidationError before our field_validator runs
        with pytest.raises((OnexError, ValidationError)):
            ModelNumericValue(value="not a number", value_type=EnumNumericType.INTEGER)

    def test_invalid_value_type_list(self):
        """Test that list value raises error."""
        # Pydantic raises ValidationError before our field_validator runs
        with pytest.raises((OnexError, ValidationError)):
            ModelNumericValue(value=[1, 2, 3], value_type=EnumNumericType.INTEGER)

    def test_invalid_value_type_dict(self):
        """Test that dict value raises error."""
        # Pydantic raises ValidationError before our field_validator runs
        with pytest.raises((OnexError, ValidationError)):
            ModelNumericValue(value={"num": 42}, value_type=EnumNumericType.INTEGER)

    def test_invalid_value_type_none(self):
        """Test that None value raises error."""
        # Pydantic raises ValidationError before our field_validator runs
        with pytest.raises((OnexError, ValidationError)):
            ModelNumericValue(value=None, value_type=EnumNumericType.INTEGER)


@pytest.mark.unit
class TestModelNumericValueRetrieval:
    """Tests for retrieving values from ModelNumericValue."""

    def test_as_int(self):
        """Test as_int method."""
        value = ModelNumericValue.from_float(3.99)
        assert value.as_int() == 3

    def test_as_float(self):
        """Test as_float method."""
        value = ModelNumericValue.from_int(42)
        assert value.as_float() == 42.0

    def test_integer_value_property(self):
        """Test integer_value property."""
        value = ModelNumericValue.from_float(3.99)
        assert value.integer_value == 3

    def test_float_value_property(self):
        """Test float_value property."""
        value = ModelNumericValue.from_int(42)
        assert value.float_value == 42.0

    def test_to_python_value_integer(self):
        """Test to_python_value for integer type."""
        value = ModelNumericValue.from_int(42)
        result = value.to_python_value()
        assert result == 42
        assert isinstance(result, int)

    def test_to_python_value_float(self):
        """Test to_python_value for float type."""
        value = ModelNumericValue.from_float(3.14)
        result = value.to_python_value()
        assert result == 3.14
        assert isinstance(result, float)

    def test_to_original_type_integer(self):
        """Test to_original_type for integer."""
        value = ModelNumericValue.from_int(42)
        result = value.to_original_type()
        assert result == 42.0

    def test_to_original_type_float(self):
        """Test to_original_type for float."""
        value = ModelNumericValue.from_float(3.14)
        result = value.to_original_type()
        assert result == 3.14


@pytest.mark.unit
class TestModelNumericValueComparison:
    """Tests for ModelNumericValue comparison."""

    def test_compare_value_equal(self):
        """Test comparing equal values."""
        value1 = ModelNumericValue.from_int(42)
        value2 = ModelNumericValue.from_int(42)
        assert value1.compare_value(value2) is True

    def test_compare_value_different(self):
        """Test comparing different values."""
        value1 = ModelNumericValue.from_int(42)
        value2 = ModelNumericValue.from_int(43)
        assert value1.compare_value(value2) is False

    def test_compare_with_float(self):
        """Test compare_with_float method."""
        value = ModelNumericValue.from_int(42)
        assert value.compare_with_float(42.0) is True
        assert value.compare_with_float(43.0) is False

    def test_equality_operator_with_numeric_value(self):
        """Test equality operator with another ModelNumericValue."""
        value1 = ModelNumericValue.from_int(42)
        value2 = ModelNumericValue.from_int(42)
        assert value1 == value2

    def test_equality_operator_with_int(self):
        """Test equality operator with raw int."""
        value = ModelNumericValue.from_int(42)
        assert value == 42

    def test_equality_operator_with_float(self):
        """Test equality operator with raw float."""
        value = ModelNumericValue.from_float(3.14)
        assert value == 3.14

    def test_inequality_operator(self):
        """Test inequality."""
        value1 = ModelNumericValue.from_int(42)
        value2 = ModelNumericValue.from_int(43)
        assert value1 != value2

    def test_less_than(self):
        """Test less than comparison."""
        value1 = ModelNumericValue.from_int(41)
        value2 = ModelNumericValue.from_int(42)
        assert value1 < value2

    def test_less_than_or_equal(self):
        """Test less than or equal comparison."""
        value1 = ModelNumericValue.from_int(42)
        value2 = ModelNumericValue.from_int(42)
        value3 = ModelNumericValue.from_int(43)
        assert value1 <= value2
        assert value1 <= value3

    def test_greater_than(self):
        """Test greater than comparison."""
        value1 = ModelNumericValue.from_int(43)
        value2 = ModelNumericValue.from_int(42)
        assert value1 > value2

    def test_greater_than_or_equal(self):
        """Test greater than or equal comparison."""
        value1 = ModelNumericValue.from_int(42)
        value2 = ModelNumericValue.from_int(42)
        value3 = ModelNumericValue.from_int(41)
        assert value1 >= value2
        assert value1 >= value3


@pytest.mark.unit
class TestModelNumericValueSerialization:
    """Tests for ModelNumericValue serialization."""

    def test_serialize(self):
        """Test serialize method."""
        value = ModelNumericValue.from_int(42)
        data = value.serialize()
        assert isinstance(data, dict)
        assert "value" in data
        assert "value_type" in data

    def test_model_dump(self):
        """Test model_dump method."""
        value = ModelNumericValue.from_float(3.14)
        data = value.model_dump()
        assert data["value"] == 3.14
        assert data["value_type"] == EnumNumericType.FLOAT

    def test_validate_instance(self):
        """Test validate_instance method."""
        value = ModelNumericValue.from_int(42)
        assert value.validate_instance() is True


@pytest.mark.unit
class TestModelNumericValueEdgeCases:
    """Tests for ModelNumericValue edge cases."""

    def test_zero_integer(self):
        """Test numeric value with zero."""
        value = ModelNumericValue.from_int(0)
        assert value.value == 0.0
        assert value.as_int() == 0

    def test_negative_integer(self):
        """Test numeric value with negative integer."""
        value = ModelNumericValue.from_int(-42)
        assert value.value == -42.0
        assert value.as_int() == -42

    def test_negative_float(self):
        """Test numeric value with negative float."""
        value = ModelNumericValue.from_float(-3.14)
        assert value.value == -3.14

    def test_very_large_integer(self):
        """Test numeric value with very large integer."""
        large_val = 10**15
        value = ModelNumericValue.from_int(large_val)
        assert value.value == float(large_val)

    def test_very_small_float(self):
        """Test numeric value with very small float."""
        small_val = 0.0000001
        value = ModelNumericValue.from_float(small_val)
        assert value.value == small_val

    def test_float_precision(self):
        """Test float precision preservation."""
        precise_val = 3.141592653589793
        value = ModelNumericValue.from_float(precise_val)
        assert value.value == precise_val

    def test_integer_to_float_conversion(self):
        """Test that integers are stored as floats."""
        value = ModelNumericValue.from_int(42)
        assert isinstance(value.value, float)
        assert value.value == 42.0

    def test_comparison_cross_type(self):
        """Test comparison between int and float types."""
        int_value = ModelNumericValue.from_int(42)
        float_value = ModelNumericValue.from_float(42.0)
        assert int_value == float_value

    def test_source_preservation(self):
        """Test that source is preserved."""
        value = ModelNumericValue.from_int(42, source="test")
        assert value.source == "test"

    def test_validation_flag(self):
        """Test that is_validated flag is set correctly."""
        value1 = ModelNumericValue.from_int(42)
        assert value1.is_validated is True

        value2 = ModelNumericValue(value=42, value_type=EnumNumericType.INTEGER)
        assert value2.is_validated is False

    def test_equality_with_non_numeric(self):
        """Test equality with non-numeric types returns False."""
        value = ModelNumericValue.from_int(42)
        assert (value == "42") is False
        assert (value == [42]) is False
        assert (value == {"val": 42}) is False
