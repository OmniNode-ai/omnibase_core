"""
Comprehensive tests for ModelNumericStringValue.

Tests cover:
- Basic creation (15 tests)
- Type discrimination (10 tests)
- Type guards (10 tests)
- Float conversion (15 tests)
- Int conversion (20 tests)
- String conversion (10 tests)
- Coercion modes (15 tests)
- String parsing (10 tests)
- JSON serialization (10 tests)
- Edge cases (10 tests)

Total: 115+ tests
"""

import json
import math

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_numeric_value_type import EnumNumericValueType
from omnibase_core.models.common.model_coercion_mode import EnumCoercionMode
from omnibase_core.models.common.model_numeric_string_value import (
    ModelNumericStringValue,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# ============================================================================
# Part 1: Basic Creation (15 tests)
# ============================================================================


class TestBasicCreation:
    """Test basic creation of ModelNumericStringValue instances."""

    def test_from_int_basic(self):
        """Test creating from integer."""
        value = ModelNumericStringValue.from_int(42)
        assert value.int_value == 42
        assert value.value_type == EnumNumericValueType.INT
        assert value.float_value is None
        assert value.str_value is None

    def test_from_int_zero(self):
        """Test creating from zero."""
        value = ModelNumericStringValue.from_int(0)
        assert value.int_value == 0
        assert value.value_type == EnumNumericValueType.INT

    def test_from_int_negative(self):
        """Test creating from negative integer."""
        value = ModelNumericStringValue.from_int(-42)
        assert value.int_value == -42
        assert value.value_type == EnumNumericValueType.INT

    def test_from_float_basic(self):
        """Test creating from float."""
        value = ModelNumericStringValue.from_float(3.14)
        assert value.float_value == 3.14
        assert value.value_type == EnumNumericValueType.FLOAT
        assert value.int_value is None
        assert value.str_value is None

    def test_from_float_zero(self):
        """Test creating from zero float."""
        value = ModelNumericStringValue.from_float(0.0)
        assert value.float_value == 0.0
        assert value.value_type == EnumNumericValueType.FLOAT

    def test_from_float_negative(self):
        """Test creating from negative float."""
        value = ModelNumericStringValue.from_float(-3.14)
        assert value.float_value == -3.14
        assert value.value_type == EnumNumericValueType.FLOAT

    def test_from_str_basic(self):
        """Test creating from string."""
        value = ModelNumericStringValue.from_str("test")
        assert value.str_value == "test"
        assert value.value_type == EnumNumericValueType.STRING
        assert value.int_value is None
        assert value.float_value is None

    def test_from_str_empty(self):
        """Test creating from empty string."""
        value = ModelNumericStringValue.from_str("")
        assert value.str_value == ""
        assert value.value_type == EnumNumericValueType.STRING

    def test_from_str_numeric(self):
        """Test creating from numeric string."""
        value = ModelNumericStringValue.from_str("123")
        assert value.str_value == "123"
        assert value.value_type == EnumNumericValueType.STRING

    def test_from_str_float_string(self):
        """Test creating from float-like string."""
        value = ModelNumericStringValue.from_str("3.14")
        assert value.str_value == "3.14"
        assert value.value_type == EnumNumericValueType.STRING

    def test_with_metadata(self):
        """Test creating with metadata."""
        metadata = {"source": "config", "env": "prod"}
        value = ModelNumericStringValue.from_int(42, metadata=metadata)
        assert value.metadata == metadata

    def test_from_any_int(self):
        """Test from_any with integer."""
        value = ModelNumericStringValue.from_any(42)
        assert value.int_value == 42
        assert value.value_type == EnumNumericValueType.INT

    def test_from_any_float(self):
        """Test from_any with float."""
        value = ModelNumericStringValue.from_any(3.14)
        assert value.float_value == 3.14
        assert value.value_type == EnumNumericValueType.FLOAT

    def test_from_any_str(self):
        """Test from_any with string."""
        value = ModelNumericStringValue.from_any("test")
        assert value.str_value == "test"
        assert value.value_type == EnumNumericValueType.STRING

    def test_from_any_bool_rejected(self):
        """Test that from_any rejects boolean values."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelNumericStringValue.from_any(True)
        assert "Boolean" in str(exc_info.value)


# ============================================================================
# Part 2: Type Discrimination (10 tests)
# ============================================================================


class TestTypeDiscrimination:
    """Test type discrimination and validation."""

    def test_correct_type_int(self):
        """Test int type is correctly identified."""
        value = ModelNumericStringValue.from_int(42)
        assert value.value_type == EnumNumericValueType.INT

    def test_correct_type_float(self):
        """Test float type is correctly identified."""
        value = ModelNumericStringValue.from_float(3.14)
        assert value.value_type == EnumNumericValueType.FLOAT

    def test_correct_type_string(self):
        """Test string type is correctly identified."""
        value = ModelNumericStringValue.from_str("test")
        assert value.value_type == EnumNumericValueType.STRING

    def test_only_one_value_set_int(self):
        """Test only int_value is set for INT type."""
        value = ModelNumericStringValue.from_int(42)
        assert value.int_value is not None
        assert value.float_value is None
        assert value.str_value is None

    def test_only_one_value_set_float(self):
        """Test only float_value is set for FLOAT type."""
        value = ModelNumericStringValue.from_float(3.14)
        assert value.float_value is not None
        assert value.int_value is None
        assert value.str_value is None

    def test_only_one_value_set_string(self):
        """Test only str_value is set for STRING type."""
        value = ModelNumericStringValue.from_str("test")
        assert value.str_value is not None
        assert value.int_value is None
        assert value.float_value is None

    def test_validation_rejects_multiple_values(self):
        """Test validation rejects multiple non-None values."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelNumericStringValue(
                value_type=EnumNumericValueType.INT,
                int_value=42,
                float_value=3.14,
            )
        assert "Exactly one value must be set" in str(exc_info.value)

    def test_validation_rejects_no_values(self):
        """Test validation rejects all None values."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelNumericStringValue(
                value_type=EnumNumericValueType.INT,
            )
        assert "Exactly one value must be set" in str(exc_info.value)

    def test_validation_rejects_wrong_value_type(self):
        """Test validation rejects wrong value for type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelNumericStringValue(
                value_type=EnumNumericValueType.INT,
                float_value=3.14,
            )
        # The validator catches this as "Required value for type 'int' is None"
        # because int_value is None even though float_value is set
        assert "Required value for type" in str(exc_info.value)

    def test_validation_rejects_nan(self):
        """Test validation rejects NaN float values."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelNumericStringValue.from_float(float("nan"))
        assert "NaN" in str(exc_info.value)


# ============================================================================
# Part 3: Type Guards (10 tests)
# ============================================================================


class TestTypeGuards:
    """Test type guard methods."""

    def test_is_float_true(self):
        """Test is_float() returns True for float."""
        value = ModelNumericStringValue.from_float(3.14)
        assert value.is_float() is True

    def test_is_float_false(self):
        """Test is_float() returns False for non-float."""
        assert ModelNumericStringValue.from_int(42).is_float() is False
        assert ModelNumericStringValue.from_str("test").is_float() is False

    def test_is_int_true(self):
        """Test is_int() returns True for int."""
        value = ModelNumericStringValue.from_int(42)
        assert value.is_int() is True

    def test_is_int_false(self):
        """Test is_int() returns False for non-int."""
        assert ModelNumericStringValue.from_float(3.14).is_int() is False
        assert ModelNumericStringValue.from_str("test").is_int() is False

    def test_is_string_true(self):
        """Test is_string() returns True for string."""
        value = ModelNumericStringValue.from_str("test")
        assert value.is_string() is True

    def test_is_string_false(self):
        """Test is_string() returns False for non-string."""
        assert ModelNumericStringValue.from_int(42).is_string() is False
        assert ModelNumericStringValue.from_float(3.14).is_string() is False

    def test_is_numeric_int(self):
        """Test is_numeric() returns True for int."""
        value = ModelNumericStringValue.from_int(42)
        assert value.is_numeric() is True

    def test_is_numeric_float(self):
        """Test is_numeric() returns True for float."""
        value = ModelNumericStringValue.from_float(3.14)
        assert value.is_numeric() is True

    def test_is_numeric_string(self):
        """Test is_numeric() returns False for string."""
        value = ModelNumericStringValue.from_str("test")
        assert value.is_numeric() is False

    def test_is_type(self):
        """Test is_type() method."""
        assert ModelNumericStringValue.from_int(42).is_type(int) is True
        assert ModelNumericStringValue.from_int(42).is_type(float) is False
        assert ModelNumericStringValue.from_float(3.14).is_type(float) is True
        assert ModelNumericStringValue.from_str("test").is_type(str) is True


# ============================================================================
# Part 4: Float Conversion (15 tests)
# ============================================================================


class TestFloatConversion:
    """Test conversion to float."""

    def test_get_as_float_from_float(self):
        """Test get_as_float() from float value."""
        value = ModelNumericStringValue.from_float(3.14)
        assert value.get_as_float() == 3.14

    def test_get_as_float_from_int(self):
        """Test get_as_float() from int value."""
        value = ModelNumericStringValue.from_int(42)
        assert value.get_as_float() == 42.0

    def test_get_as_float_from_int_zero(self):
        """Test get_as_float() from zero int."""
        value = ModelNumericStringValue.from_int(0)
        assert value.get_as_float() == 0.0

    def test_get_as_float_from_int_negative(self):
        """Test get_as_float() from negative int."""
        value = ModelNumericStringValue.from_int(-42)
        assert value.get_as_float() == -42.0

    def test_get_as_float_from_str_int(self):
        """Test get_as_float() from integer string."""
        value = ModelNumericStringValue.from_str("42")
        assert value.get_as_float() == 42.0

    def test_get_as_float_from_str_float(self):
        """Test get_as_float() from float string."""
        value = ModelNumericStringValue.from_str("3.14")
        assert value.get_as_float() == 3.14

    def test_get_as_float_from_str_negative(self):
        """Test get_as_float() from negative string."""
        value = ModelNumericStringValue.from_str("-3.14")
        assert value.get_as_float() == -3.14

    def test_get_as_float_from_str_scientific(self):
        """Test get_as_float() from scientific notation string."""
        value = ModelNumericStringValue.from_str("1e5")
        assert value.get_as_float() == 100000.0

    def test_get_as_float_from_str_zero(self):
        """Test get_as_float() from zero string."""
        value = ModelNumericStringValue.from_str("0")
        assert value.get_as_float() == 0.0

    def test_get_as_float_from_str_zero_float(self):
        """Test get_as_float() from zero float string."""
        value = ModelNumericStringValue.from_str("0.0")
        assert value.get_as_float() == 0.0

    def test_get_as_float_from_str_invalid(self):
        """Test get_as_float() raises error for invalid string."""
        value = ModelNumericStringValue.from_str("not_a_number")
        with pytest.raises(ModelOnexError) as exc_info:
            value.get_as_float()
        assert "Cannot convert string" in str(exc_info.value)

    def test_get_as_float_from_str_empty(self):
        """Test get_as_float() raises error for empty string."""
        value = ModelNumericStringValue.from_str("")
        with pytest.raises(ModelOnexError) as exc_info:
            value.get_as_float()
        assert "Cannot convert string" in str(exc_info.value)

    def test_get_as_float_from_str_whitespace(self):
        """Test get_as_float() from string with whitespace."""
        value = ModelNumericStringValue.from_str("  42.5  ")
        assert value.get_as_float() == 42.5

    def test_get_as_float_precision(self):
        """Test get_as_float() preserves precision."""
        value = ModelNumericStringValue.from_float(3.141592653589793)
        assert value.get_as_float() == 3.141592653589793

    def test_get_as_float_very_small(self):
        """Test get_as_float() with very small number."""
        value = ModelNumericStringValue.from_float(0.0000001)
        assert value.get_as_float() == 0.0000001


# ============================================================================
# Part 5: Int Conversion (20 tests)
# ============================================================================


class TestIntConversion:
    """Test conversion to int with coercion modes."""

    def test_get_as_int_from_int(self):
        """Test get_as_int() from int value."""
        value = ModelNumericStringValue.from_int(42)
        assert value.get_as_int() == 42

    def test_get_as_int_from_int_zero(self):
        """Test get_as_int() from zero int."""
        value = ModelNumericStringValue.from_int(0)
        assert value.get_as_int() == 0

    def test_get_as_int_from_int_negative(self):
        """Test get_as_int() from negative int."""
        value = ModelNumericStringValue.from_int(-42)
        assert value.get_as_int() == -42

    def test_get_as_int_from_float_exact(self):
        """Test get_as_int() from exact float."""
        value = ModelNumericStringValue.from_float(3.0)
        assert value.get_as_int() == 3

    def test_get_as_int_from_float_strict_fails(self):
        """Test get_as_int() strict mode fails for non-exact float."""
        value = ModelNumericStringValue.from_float(3.5)
        with pytest.raises(ModelOnexError) as exc_info:
            value.get_as_int(EnumCoercionMode.STRICT)
        assert "not an exact integer" in str(exc_info.value)

    def test_get_as_int_from_float_floor(self):
        """Test get_as_int() with FLOOR mode."""
        value = ModelNumericStringValue.from_float(3.7)
        assert value.get_as_int(EnumCoercionMode.FLOOR) == 3

    def test_get_as_int_from_float_floor_negative(self):
        """Test get_as_int() FLOOR mode with negative float."""
        value = ModelNumericStringValue.from_float(-3.7)
        assert value.get_as_int(EnumCoercionMode.FLOOR) == -4

    def test_get_as_int_from_float_ceil(self):
        """Test get_as_int() with CEIL mode."""
        value = ModelNumericStringValue.from_float(3.2)
        assert value.get_as_int(EnumCoercionMode.CEIL) == 4

    def test_get_as_int_from_float_ceil_negative(self):
        """Test get_as_int() CEIL mode with negative float."""
        value = ModelNumericStringValue.from_float(-3.2)
        assert value.get_as_int(EnumCoercionMode.CEIL) == -3

    def test_get_as_int_from_float_round(self):
        """Test get_as_int() with ROUND mode."""
        value = ModelNumericStringValue.from_float(3.5)
        assert value.get_as_int(EnumCoercionMode.ROUND) == 4

    def test_get_as_int_from_float_round_down(self):
        """Test get_as_int() ROUND mode rounds down."""
        value = ModelNumericStringValue.from_float(3.4)
        assert value.get_as_int(EnumCoercionMode.ROUND) == 3

    def test_get_as_int_from_str_int(self):
        """Test get_as_int() from integer string."""
        value = ModelNumericStringValue.from_str("42")
        assert value.get_as_int() == 42

    def test_get_as_int_from_str_negative(self):
        """Test get_as_int() from negative string."""
        value = ModelNumericStringValue.from_str("-42")
        assert value.get_as_int() == -42

    def test_get_as_int_from_str_float_exact(self):
        """Test get_as_int() from exact float string."""
        value = ModelNumericStringValue.from_str("3.0")
        assert value.get_as_int() == 3

    def test_get_as_int_from_str_float_round(self):
        """Test get_as_int() from float string with ROUND."""
        value = ModelNumericStringValue.from_str("3.7")
        assert value.get_as_int(EnumCoercionMode.ROUND) == 4

    def test_get_as_int_from_str_float_strict_fails(self):
        """Test get_as_int() strict fails for non-exact float string."""
        value = ModelNumericStringValue.from_str("3.5")
        with pytest.raises(ModelOnexError) as exc_info:
            value.get_as_int(EnumCoercionMode.STRICT)
        assert "non-exact float" in str(exc_info.value)

    def test_get_as_int_from_str_invalid(self):
        """Test get_as_int() raises error for invalid string."""
        value = ModelNumericStringValue.from_str("not_a_number")
        with pytest.raises(ModelOnexError) as exc_info:
            value.get_as_int()
        assert "Cannot convert string" in str(exc_info.value)

    def test_get_as_int_from_str_empty(self):
        """Test get_as_int() raises error for empty string."""
        value = ModelNumericStringValue.from_str("")
        with pytest.raises(ModelOnexError) as exc_info:
            value.get_as_int()
        assert "Cannot convert string" in str(exc_info.value)

    def test_get_as_int_from_str_whitespace(self):
        """Test get_as_int() from string with whitespace."""
        value = ModelNumericStringValue.from_str("  42  ")
        assert value.get_as_int() == 42

    def test_get_as_int_large_number(self):
        """Test get_as_int() with large number."""
        value = ModelNumericStringValue.from_int(10**15)
        assert value.get_as_int() == 10**15


# ============================================================================
# Part 6: String Conversion (10 tests)
# ============================================================================


class TestStringConversion:
    """Test conversion to string."""

    def test_get_as_str_from_str(self):
        """Test get_as_str() from string value."""
        value = ModelNumericStringValue.from_str("test")
        assert value.get_as_str() == "test"

    def test_get_as_str_from_str_empty(self):
        """Test get_as_str() from empty string."""
        value = ModelNumericStringValue.from_str("")
        assert value.get_as_str() == ""

    def test_get_as_str_from_int(self):
        """Test get_as_str() from int value."""
        value = ModelNumericStringValue.from_int(42)
        assert value.get_as_str() == "42"

    def test_get_as_str_from_int_zero(self):
        """Test get_as_str() from zero int."""
        value = ModelNumericStringValue.from_int(0)
        assert value.get_as_str() == "0"

    def test_get_as_str_from_int_negative(self):
        """Test get_as_str() from negative int."""
        value = ModelNumericStringValue.from_int(-42)
        assert value.get_as_str() == "-42"

    def test_get_as_str_from_float(self):
        """Test get_as_str() from float value."""
        value = ModelNumericStringValue.from_float(3.14)
        assert value.get_as_str() == "3.14"

    def test_get_as_str_from_float_zero(self):
        """Test get_as_str() from zero float."""
        value = ModelNumericStringValue.from_float(0.0)
        assert value.get_as_str() == "0.0"

    def test_get_as_str_from_float_negative(self):
        """Test get_as_str() from negative float."""
        value = ModelNumericStringValue.from_float(-3.14)
        assert value.get_as_str() == "-3.14"

    def test_get_as_str_preserves_format(self):
        """Test get_as_str() preserves string format."""
        value = ModelNumericStringValue.from_str("  test  ")
        assert value.get_as_str() == "  test  "

    def test_get_as_str_numeric_string(self):
        """Test get_as_str() preserves numeric string."""
        value = ModelNumericStringValue.from_str("123")
        assert value.get_as_str() == "123"


# ============================================================================
# Part 7: Coercion Modes (15 tests)
# ============================================================================


class TestCoercionModes:
    """Test coercion mode behavior."""

    def test_coercion_strict_exact_float(self):
        """Test STRICT mode allows exact float."""
        value = ModelNumericStringValue.from_float(3.0)
        assert value.get_as_int(EnumCoercionMode.STRICT) == 3

    def test_coercion_strict_fails_non_exact(self):
        """Test STRICT mode fails for non-exact float."""
        value = ModelNumericStringValue.from_float(3.5)
        with pytest.raises(ModelOnexError):
            value.get_as_int(EnumCoercionMode.STRICT)

    def test_coercion_floor_positive(self):
        """Test FLOOR mode with positive number."""
        assert (
            ModelNumericStringValue.from_float(3.9).get_as_int(EnumCoercionMode.FLOOR)
            == 3
        )
        assert (
            ModelNumericStringValue.from_float(3.1).get_as_int(EnumCoercionMode.FLOOR)
            == 3
        )

    def test_coercion_floor_negative(self):
        """Test FLOOR mode with negative number."""
        assert (
            ModelNumericStringValue.from_float(-3.1).get_as_int(EnumCoercionMode.FLOOR)
            == -4
        )
        assert (
            ModelNumericStringValue.from_float(-3.9).get_as_int(EnumCoercionMode.FLOOR)
            == -4
        )

    def test_coercion_ceil_positive(self):
        """Test CEIL mode with positive number."""
        assert (
            ModelNumericStringValue.from_float(3.1).get_as_int(EnumCoercionMode.CEIL)
            == 4
        )
        assert (
            ModelNumericStringValue.from_float(3.9).get_as_int(EnumCoercionMode.CEIL)
            == 4
        )

    def test_coercion_ceil_negative(self):
        """Test CEIL mode with negative number."""
        assert (
            ModelNumericStringValue.from_float(-3.1).get_as_int(EnumCoercionMode.CEIL)
            == -3
        )
        assert (
            ModelNumericStringValue.from_float(-3.9).get_as_int(EnumCoercionMode.CEIL)
            == -3
        )

    def test_coercion_round_half_up(self):
        """Test ROUND mode rounds half up."""
        assert (
            ModelNumericStringValue.from_float(3.5).get_as_int(EnumCoercionMode.ROUND)
            == 4
        )

    def test_coercion_round_half_down(self):
        """Test ROUND mode rounds half down."""
        assert (
            ModelNumericStringValue.from_float(3.4).get_as_int(EnumCoercionMode.ROUND)
            == 3
        )

    def test_coercion_round_negative(self):
        """Test ROUND mode with negative number."""
        assert (
            ModelNumericStringValue.from_float(-3.5).get_as_int(EnumCoercionMode.ROUND)
            == -4
        )
        assert (
            ModelNumericStringValue.from_float(-3.4).get_as_int(EnumCoercionMode.ROUND)
            == -3
        )

    def test_coercion_default_is_strict(self):
        """Test default coercion mode is STRICT."""
        value = ModelNumericStringValue.from_float(3.0)
        assert value.get_as_int() == 3

        value2 = ModelNumericStringValue.from_float(3.5)
        with pytest.raises(ModelOnexError):
            value2.get_as_int()

    def test_coercion_on_string_floor(self):
        """Test coercion works on parsed strings - FLOOR."""
        value = ModelNumericStringValue.from_str("3.7")
        assert value.get_as_int(EnumCoercionMode.FLOOR) == 3

    def test_coercion_on_string_ceil(self):
        """Test coercion works on parsed strings - CEIL."""
        value = ModelNumericStringValue.from_str("3.2")
        assert value.get_as_int(EnumCoercionMode.CEIL) == 4

    def test_coercion_on_string_round(self):
        """Test coercion works on parsed strings - ROUND."""
        value = ModelNumericStringValue.from_str("3.5")
        assert value.get_as_int(EnumCoercionMode.ROUND) == 4

    def test_coercion_on_string_strict_exact(self):
        """Test STRICT coercion on exact float string."""
        value = ModelNumericStringValue.from_str("3.0")
        assert value.get_as_int(EnumCoercionMode.STRICT) == 3

    def test_coercion_on_string_strict_fails(self):
        """Test STRICT coercion fails on non-exact float string."""
        value = ModelNumericStringValue.from_str("3.5")
        with pytest.raises(ModelOnexError):
            value.get_as_int(EnumCoercionMode.STRICT)


# ============================================================================
# Part 8: String Parsing (10 tests)
# ============================================================================


class TestStringParsing:
    """Test parsing of various string formats."""

    def test_parse_simple_int(self):
        """Test parsing simple integer string."""
        value = ModelNumericStringValue.from_str("123")
        assert value.get_as_int() == 123

    def test_parse_simple_float(self):
        """Test parsing simple float string."""
        value = ModelNumericStringValue.from_str("45.67")
        assert value.get_as_float() == 45.67

    def test_parse_scientific_notation(self):
        """Test parsing scientific notation."""
        value = ModelNumericStringValue.from_str("1e5")
        assert value.get_as_float() == 100000.0

    def test_parse_scientific_negative(self):
        """Test parsing negative scientific notation."""
        value = ModelNumericStringValue.from_str("1e-3")
        assert value.get_as_float() == 0.001

    def test_parse_leading_zeros(self):
        """Test parsing number with leading zeros."""
        value = ModelNumericStringValue.from_str("00123")
        assert value.get_as_int() == 123

    def test_parse_with_whitespace(self):
        """Test parsing number with whitespace."""
        value = ModelNumericStringValue.from_str("  42  ")
        assert value.get_as_int() == 42

    def test_parse_negative_int(self):
        """Test parsing negative integer."""
        value = ModelNumericStringValue.from_str("-123")
        assert value.get_as_int() == -123

    def test_parse_negative_float(self):
        """Test parsing negative float."""
        value = ModelNumericStringValue.from_str("-45.67")
        assert value.get_as_float() == -45.67

    def test_parse_invalid_string(self):
        """Test parsing invalid string fails."""
        value = ModelNumericStringValue.from_str("not_a_number")
        with pytest.raises(ModelOnexError):
            value.get_as_int()
        with pytest.raises(ModelOnexError):
            value.get_as_float()

    def test_parse_mixed_content(self):
        """Test parsing string with mixed content fails."""
        value = ModelNumericStringValue.from_str("123abc")
        with pytest.raises(ModelOnexError):
            value.get_as_int()


# ============================================================================
# Part 9: JSON Serialization (10 tests)
# ============================================================================


class TestJSONSerialization:
    """Test JSON serialization and deserialization."""

    def test_model_dump_int(self):
        """Test model_dump() for int value."""
        value = ModelNumericStringValue.from_int(42)
        data = value.model_dump()
        assert data["int_value"] == 42
        assert data["value_type"] == EnumNumericValueType.INT
        assert data["float_value"] is None
        assert data["str_value"] is None

    def test_model_dump_float(self):
        """Test model_dump() for float value."""
        value = ModelNumericStringValue.from_float(3.14)
        data = value.model_dump()
        assert data["float_value"] == 3.14
        assert data["value_type"] == EnumNumericValueType.FLOAT

    def test_model_dump_string(self):
        """Test model_dump() for string value."""
        value = ModelNumericStringValue.from_str("test")
        data = value.model_dump()
        assert data["str_value"] == "test"
        assert data["value_type"] == EnumNumericValueType.STRING

    def test_model_dump_json_int(self):
        """Test model_dump_json() for int value."""
        value = ModelNumericStringValue.from_int(42)
        json_str = value.model_dump_json()
        data = json.loads(json_str)
        assert data["int_value"] == 42
        assert data["value_type"] == "int"

    def test_model_dump_json_float(self):
        """Test model_dump_json() for float value."""
        value = ModelNumericStringValue.from_float(3.14)
        json_str = value.model_dump_json()
        data = json.loads(json_str)
        assert data["float_value"] == 3.14

    def test_model_validate_from_dict(self):
        """Test model_validate() from dictionary."""
        data = {
            "value_type": EnumNumericValueType.INT,
            "int_value": 42,
        }
        value = ModelNumericStringValue.model_validate(data)
        assert value.int_value == 42

    def test_model_validate_json(self):
        """Test model_validate_json() from JSON string."""
        json_str = '{"value_type": "int", "int_value": 42}'
        value = ModelNumericStringValue.model_validate_json(json_str)
        assert value.int_value == 42

    def test_round_trip_int(self):
        """Test round-trip serialization for int."""
        original = ModelNumericStringValue.from_int(42)
        json_str = original.model_dump_json()
        restored = ModelNumericStringValue.model_validate_json(json_str)
        assert restored.int_value == original.int_value
        assert restored.value_type == original.value_type

    def test_round_trip_float(self):
        """Test round-trip serialization for float."""
        original = ModelNumericStringValue.from_float(3.14)
        json_str = original.model_dump_json()
        restored = ModelNumericStringValue.model_validate_json(json_str)
        assert restored.float_value == original.float_value

    def test_round_trip_string(self):
        """Test round-trip serialization for string."""
        original = ModelNumericStringValue.from_str("test")
        json_str = original.model_dump_json()
        restored = ModelNumericStringValue.model_validate_json(json_str)
        assert restored.str_value == original.str_value


# ============================================================================
# Part 10: Edge Cases (10+ tests)
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_int(self):
        """Test zero integer value."""
        value = ModelNumericStringValue.from_int(0)
        assert value.get_as_int() == 0
        assert value.get_as_float() == 0.0
        assert value.get_as_str() == "0"

    def test_zero_float(self):
        """Test zero float value."""
        value = ModelNumericStringValue.from_float(0.0)
        assert value.get_as_float() == 0.0
        assert value.get_as_int() == 0
        assert value.get_as_str() == "0.0"

    def test_negative_zero(self):
        """Test negative zero."""
        value = ModelNumericStringValue.from_float(-0.0)
        assert value.get_as_float() == 0.0

    def test_very_large_int(self):
        """Test very large integer."""
        large = 10**18
        value = ModelNumericStringValue.from_int(large)
        assert value.get_as_int() == large

    def test_very_small_float(self):
        """Test very small float."""
        small = 1e-10
        value = ModelNumericStringValue.from_float(small)
        assert value.get_as_float() == small

    def test_infinity_rejected(self):
        """Test infinity is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelNumericStringValue.from_float(float("inf"))
        assert "infinity" in str(exc_info.value)

    def test_negative_infinity_rejected(self):
        """Test negative infinity is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelNumericStringValue.from_float(float("-inf"))
        assert "infinity" in str(exc_info.value)

    def test_equality_same_type_same_value(self):
        """Test equality for same type and value."""
        v1 = ModelNumericStringValue.from_int(42)
        v2 = ModelNumericStringValue.from_int(42)
        assert v1 == v2

    def test_equality_different_values(self):
        """Test inequality for different values."""
        v1 = ModelNumericStringValue.from_int(42)
        v2 = ModelNumericStringValue.from_int(43)
        assert v1 != v2

    def test_equality_different_types(self):
        """Test inequality for different types with same value."""
        v1 = ModelNumericStringValue.from_int(42)
        v2 = ModelNumericStringValue.from_str("42")
        assert v1 != v2  # Different types even if values could be equal

    def test_str_representation(self):
        """Test __str__() method."""
        value = ModelNumericStringValue.from_int(42)
        assert "42" in str(value)
        assert "NumericStringValue" in str(value)

    def test_repr_representation(self):
        """Test __repr__() method."""
        value = ModelNumericStringValue.from_int(42)
        repr_str = repr(value)
        assert "ModelNumericStringValue" in repr_str
        assert "42" in repr_str

    def test_get_type(self):
        """Test get_type() method."""
        assert ModelNumericStringValue.from_int(42).get_type() == int
        assert ModelNumericStringValue.from_float(3.14).get_type() == float
        assert ModelNumericStringValue.from_str("test").get_type() == str

    def test_get_value(self):
        """Test get_value() method."""
        assert ModelNumericStringValue.from_int(42).get_value() == 42
        assert ModelNumericStringValue.from_float(3.14).get_value() == 3.14
        assert ModelNumericStringValue.from_str("test").get_value() == "test"
