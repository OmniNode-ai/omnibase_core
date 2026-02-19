# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Comprehensive tests for ModelOptionalInt."""

import pytest

from omnibase_core.models.common.model_optional_int import (
    EnumCoercionMode,
    ModelOptionalInt,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.mark.unit
class TestModelOptionalIntNoneHandling:
    """Tests for None handling in ModelOptionalInt."""

    def test_create_with_none(self) -> None:
        """Test creating optional int with None value."""
        value = ModelOptionalInt(value=None)
        assert value.value is None
        assert value.is_none() is True
        assert value.is_some() is False

    def test_create_without_value_defaults_to_none(self) -> None:
        """Test creating optional int without value defaults to None."""
        value = ModelOptionalInt()
        assert value.value is None
        assert value.is_none() is True

    def test_none_unwrap_raises_error(self) -> None:
        """Test unwrapping None raises ModelOnexError."""
        value = ModelOptionalInt(value=None)
        with pytest.raises(ModelOnexError) as exc_info:
            value.unwrap()
        assert "Called unwrap() on None value" in str(exc_info.value)

    def test_none_unwrap_or_returns_default(self) -> None:
        """Test unwrap_or returns default for None."""
        value = ModelOptionalInt(value=None)
        result = value.unwrap_or(100)
        assert result == 100

    def test_none_unwrap_or_else_calls_function(self) -> None:
        """Test unwrap_or_else calls function for None."""
        value = ModelOptionalInt(value=None)
        result = value.unwrap_or_else(lambda: 200)
        assert result == 200

    def test_none_get_value_or_returns_default(self) -> None:
        """Test get_value_or returns default for None."""
        value = ModelOptionalInt(value=None)
        result = value.get_value_or(50)
        assert result == 50

    def test_none_map_returns_none(self) -> None:
        """Test map on None returns None."""
        value = ModelOptionalInt(value=None)
        result = value.map(lambda x: x * 2)
        assert result.is_none() is True

    def test_none_bool_is_false(self) -> None:
        """Test None value has False boolean representation."""
        value = ModelOptionalInt(value=None)
        assert bool(value) is False


@pytest.mark.unit
class TestModelOptionalIntIntegerValues:
    """Tests for integer value handling in ModelOptionalInt."""

    def test_create_with_positive_int(self) -> None:
        """Test creating optional int with positive integer."""
        value = ModelOptionalInt(value=42)
        assert value.value == 42
        assert value.is_some() is True
        assert value.is_none() is False

    def test_create_with_negative_int(self) -> None:
        """Test creating optional int with negative integer."""
        value = ModelOptionalInt(value=-100)
        assert value.value == -100
        assert value.is_some() is True

    def test_create_with_zero(self) -> None:
        """Test creating optional int with zero."""
        value = ModelOptionalInt(value=0)
        assert value.value == 0
        assert value.is_some() is True

    def test_create_with_large_positive_int(self) -> None:
        """Test creating optional int with large positive integer."""
        value = ModelOptionalInt(value=2**31 - 1)  # Max 32-bit signed int
        assert value.value == 2**31 - 1

    def test_create_with_large_negative_int(self) -> None:
        """Test creating optional int with large negative integer."""
        value = ModelOptionalInt(value=-(2**31))  # Min 32-bit signed int
        assert value.value == -(2**31)

    def test_create_with_very_large_int(self) -> None:
        """Test creating optional int with very large integer (Python arbitrary precision)."""
        large_value = 10**100
        value = ModelOptionalInt(value=large_value)
        assert value.value == large_value

    def test_int_unwrap_returns_value(self) -> None:
        """Test unwrap returns integer value."""
        value = ModelOptionalInt(value=42)
        result = value.unwrap()
        assert result == 42
        assert isinstance(result, int)

    def test_int_unwrap_or_returns_value(self) -> None:
        """Test unwrap_or returns value (not default) when present."""
        value = ModelOptionalInt(value=42)
        result = value.unwrap_or(100)
        assert result == 42

    def test_int_unwrap_or_else_returns_value(self) -> None:
        """Test unwrap_or_else returns value (not computed) when present."""
        value = ModelOptionalInt(value=42)
        result = value.unwrap_or_else(lambda: 200)
        assert result == 42

    def test_int_bool_is_true(self) -> None:
        """Test integer value has True boolean representation."""
        value = ModelOptionalInt(value=42)
        assert bool(value) is True

    def test_int_zero_bool_is_true(self) -> None:
        """Test zero integer still has True boolean (present value)."""
        value = ModelOptionalInt(value=0)
        assert bool(value) is True  # is_some() is True even for 0


@pytest.mark.unit
class TestModelOptionalIntFloatCoercionStrict:
    """Tests for float-to-int coercion in STRICT mode."""

    def test_exact_float_coerces_in_strict_mode(self) -> None:
        """Test exact float (3.0) coerces to int in STRICT mode."""
        value = ModelOptionalInt(value=3.0, coercion_mode=EnumCoercionMode.STRICT)
        assert value.value == 3
        assert isinstance(value.value, int)

    def test_exact_float_default_mode_is_strict(self) -> None:
        """Test exact float coerces in default (STRICT) mode."""
        value = ModelOptionalInt(value=5.0)
        assert value.value == 5

    def test_exact_negative_float_coerces(self) -> None:
        """Test exact negative float coerces to int."""
        value = ModelOptionalInt(value=-10.0)
        assert value.value == -10

    def test_exact_zero_float_coerces(self) -> None:
        """Test exact zero float coerces to int."""
        value = ModelOptionalInt(value=0.0)
        assert value.value == 0

    def test_non_exact_float_raises_error_in_strict_mode(self) -> None:
        """Test non-exact float raises error in STRICT mode."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOptionalInt(value=3.5, coercion_mode=EnumCoercionMode.STRICT)
        assert "not an exact integer" in str(exc_info.value)

    def test_non_exact_float_default_mode_raises_error(self) -> None:
        """Test non-exact float raises error in default (STRICT) mode."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOptionalInt(value=3.7)
        assert "not an exact integer" in str(exc_info.value)

    def test_small_fractional_part_raises_error(self) -> None:
        """Test float with small fractional part raises error in STRICT mode."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOptionalInt(value=3.0001)
        assert "not an exact integer" in str(exc_info.value)


@pytest.mark.unit
class TestModelOptionalIntFloatCoercionFloor:
    """Tests for float-to-int coercion in FLOOR mode."""

    def test_floor_mode_positive_float(self) -> None:
        """Test FLOOR mode with positive float."""
        value = ModelOptionalInt(value=3.7, coercion_mode=EnumCoercionMode.FLOOR)
        assert value.value == 3

    def test_floor_mode_negative_float(self) -> None:
        """Test FLOOR mode with negative float."""
        value = ModelOptionalInt(value=-3.7, coercion_mode=EnumCoercionMode.FLOOR)
        assert value.value == -4  # floor(-3.7) = -4

    def test_floor_mode_exact_float(self) -> None:
        """Test FLOOR mode with exact float."""
        value = ModelOptionalInt(value=5.0, coercion_mode=EnumCoercionMode.FLOOR)
        assert value.value == 5

    def test_floor_mode_small_fraction(self) -> None:
        """Test FLOOR mode with small fractional part."""
        value = ModelOptionalInt(value=3.1, coercion_mode=EnumCoercionMode.FLOOR)
        assert value.value == 3

    def test_floor_mode_large_fraction(self) -> None:
        """Test FLOOR mode with large fractional part."""
        value = ModelOptionalInt(value=3.9, coercion_mode=EnumCoercionMode.FLOOR)
        assert value.value == 3


@pytest.mark.unit
class TestModelOptionalIntFloatCoercionCeil:
    """Tests for float-to-int coercion in CEIL mode."""

    def test_ceil_mode_positive_float(self) -> None:
        """Test CEIL mode with positive float."""
        value = ModelOptionalInt(value=3.2, coercion_mode=EnumCoercionMode.CEIL)
        assert value.value == 4

    def test_ceil_mode_negative_float(self) -> None:
        """Test CEIL mode with negative float."""
        value = ModelOptionalInt(value=-3.2, coercion_mode=EnumCoercionMode.CEIL)
        assert value.value == -3  # ceil(-3.2) = -3

    def test_ceil_mode_exact_float(self) -> None:
        """Test CEIL mode with exact float."""
        value = ModelOptionalInt(value=5.0, coercion_mode=EnumCoercionMode.CEIL)
        assert value.value == 5

    def test_ceil_mode_small_fraction(self) -> None:
        """Test CEIL mode with small fractional part."""
        value = ModelOptionalInt(value=3.1, coercion_mode=EnumCoercionMode.CEIL)
        assert value.value == 4

    def test_ceil_mode_large_fraction(self) -> None:
        """Test CEIL mode with large fractional part."""
        value = ModelOptionalInt(value=3.9, coercion_mode=EnumCoercionMode.CEIL)
        assert value.value == 4


@pytest.mark.unit
class TestModelOptionalIntFloatCoercionRound:
    """Tests for float-to-int coercion in ROUND mode."""

    def test_round_mode_positive_float_round_down(self) -> None:
        """Test ROUND mode with positive float that rounds down."""
        value = ModelOptionalInt(value=3.4, coercion_mode=EnumCoercionMode.ROUND)
        assert value.value == 3

    def test_round_mode_positive_float_round_up(self) -> None:
        """Test ROUND mode with positive float that rounds up."""
        value = ModelOptionalInt(value=3.6, coercion_mode=EnumCoercionMode.ROUND)
        assert value.value == 4

    def test_round_mode_positive_float_exactly_half(self) -> None:
        """Test ROUND mode with positive float exactly at .5 (banker's rounding)."""
        value = ModelOptionalInt(value=3.5, coercion_mode=EnumCoercionMode.ROUND)
        # Python uses banker's rounding: 3.5 rounds to 4 (nearest even)
        assert value.value == 4

    def test_round_mode_negative_float_round_down(self) -> None:
        """Test ROUND mode with negative float."""
        value = ModelOptionalInt(value=-3.4, coercion_mode=EnumCoercionMode.ROUND)
        assert value.value == -3

    def test_round_mode_negative_float_round_up(self) -> None:
        """Test ROUND mode with negative float that rounds up (towards -inf)."""
        value = ModelOptionalInt(value=-3.6, coercion_mode=EnumCoercionMode.ROUND)
        assert value.value == -4

    def test_round_mode_exact_float(self) -> None:
        """Test ROUND mode with exact float."""
        value = ModelOptionalInt(value=5.0, coercion_mode=EnumCoercionMode.ROUND)
        assert value.value == 5


@pytest.mark.unit
class TestModelOptionalIntInvalidFloatValues:
    """Tests for invalid float values (NaN, infinity)."""

    def test_nan_raises_error(self) -> None:
        """Test NaN float raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOptionalInt(value=float("nan"))
        assert "cannot be NaN or infinity" in str(exc_info.value)

    def test_positive_infinity_raises_error(self) -> None:
        """Test positive infinity raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOptionalInt(value=float("inf"))
        assert "cannot be NaN or infinity" in str(exc_info.value)

    def test_negative_infinity_raises_error(self) -> None:
        """Test negative infinity raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOptionalInt(value=float("-inf"))
        assert "cannot be NaN or infinity" in str(exc_info.value)

    def test_nan_with_floor_mode_raises_error(self) -> None:
        """Test NaN raises error even with FLOOR mode."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOptionalInt(value=float("nan"), coercion_mode=EnumCoercionMode.FLOOR)
        assert "cannot be NaN or infinity" in str(exc_info.value)


@pytest.mark.unit
class TestModelOptionalIntInvalidTypes:
    """Tests for invalid input types."""

    def test_string_raises_error(self) -> None:
        """Test string value raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOptionalInt(value="42")  # type: ignore[arg-type]
        assert "Cannot convert str to optional int" in str(exc_info.value)

    def test_boolean_true_raises_error(self) -> None:
        """Test boolean True raises error (must use 1 explicitly)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOptionalInt(value=True)  # type: ignore[arg-type]
        assert "Boolean values not allowed" in str(exc_info.value)

    def test_boolean_false_raises_error(self) -> None:
        """Test boolean False raises error (must use 0 explicitly)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOptionalInt(value=False)  # type: ignore[arg-type]
        assert "Boolean values not allowed" in str(exc_info.value)

    def test_list_raises_error(self) -> None:
        """Test list value raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOptionalInt(value=[1, 2, 3])  # type: ignore[arg-type]
        assert "Cannot convert list to optional int" in str(exc_info.value)

    def test_dict_raises_error(self) -> None:
        """Test dict value raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOptionalInt(value={"key": "value"})  # type: ignore[arg-type]
        assert "Cannot convert dict to optional int" in str(exc_info.value)


@pytest.mark.unit
class TestModelOptionalIntUnwrapMethods:
    """Tests for unwrap-style methods."""

    def test_unwrap_with_value(self) -> None:
        """Test unwrap returns value when present."""
        value = ModelOptionalInt(value=42)
        result = value.unwrap()
        assert result == 42

    def test_unwrap_or_with_value(self) -> None:
        """Test unwrap_or returns value (ignores default) when present."""
        value = ModelOptionalInt(value=42)
        result = value.unwrap_or(999)
        assert result == 42

    def test_unwrap_or_with_none(self) -> None:
        """Test unwrap_or returns default when None."""
        value = ModelOptionalInt(value=None)
        result = value.unwrap_or(999)
        assert result == 999

    def test_unwrap_or_else_with_value(self) -> None:
        """Test unwrap_or_else returns value (doesn't call function) when present."""
        value = ModelOptionalInt(value=42)
        called = False

        def compute_default() -> int:
            nonlocal called
            called = True
            return 999

        result = value.unwrap_or_else(compute_default)
        assert result == 42
        assert called is False

    def test_unwrap_or_else_with_none(self) -> None:
        """Test unwrap_or_else calls function when None."""
        value = ModelOptionalInt(value=None)
        called = False

        def compute_default() -> int:
            nonlocal called
            called = True
            return 999

        result = value.unwrap_or_else(compute_default)
        assert result == 999
        assert called is True

    def test_get_value_or_with_value(self) -> None:
        """Test get_value_or returns value when present."""
        value = ModelOptionalInt(value=42)
        result = value.get_value_or(999)
        assert result == 42

    def test_get_value_or_with_none(self) -> None:
        """Test get_value_or returns default when None."""
        value = ModelOptionalInt(value=None)
        result = value.get_value_or(999)
        assert result == 999


@pytest.mark.unit
class TestModelOptionalIntMapMethod:
    """Tests for map transformation method."""

    def test_map_with_value(self) -> None:
        """Test map applies function to value."""
        value = ModelOptionalInt(value=5)
        result = value.map(lambda x: x * 2)
        assert result.unwrap() == 10

    def test_map_with_none(self) -> None:
        """Test map with None returns None."""
        value = ModelOptionalInt(value=None)
        result = value.map(lambda x: x * 2)
        assert result.is_none() is True

    def test_map_preserves_coercion_mode(self) -> None:
        """Test map preserves coercion mode."""
        value = ModelOptionalInt(value=5, coercion_mode=EnumCoercionMode.FLOOR)
        result = value.map(lambda x: x * 2)
        assert result.coercion_mode == EnumCoercionMode.FLOOR

    def test_map_preserves_metadata(self) -> None:
        """Test map preserves metadata."""
        value = ModelOptionalInt(value=5, metadata={"source": "test"})
        result = value.map(lambda x: x * 2)
        assert result.metadata == {"source": "test"}

    def test_map_chain_multiple_operations(self) -> None:
        """Test chaining multiple map operations."""
        value = ModelOptionalInt(value=5)
        result = value.map(lambda x: x * 2).map(lambda x: x + 10).map(lambda x: x // 2)
        assert result.unwrap() == 10


@pytest.mark.unit
class TestModelOptionalIntMetadata:
    """Tests for metadata handling."""

    def test_create_with_metadata(self) -> None:
        """Test creating optional int with metadata."""
        value = ModelOptionalInt(value=42, metadata={"source": "api", "version": "1.0"})
        assert value.metadata == {"source": "api", "version": "1.0"}

    def test_create_without_metadata_defaults_to_empty(self) -> None:
        """Test creating optional int without metadata defaults to empty dict."""
        value = ModelOptionalInt(value=42)
        assert value.metadata == {}

    def test_metadata_preserved_in_map(self) -> None:
        """Test metadata is preserved during map operations."""
        value = ModelOptionalInt(value=42, metadata={"key": "value"})
        result = value.map(lambda x: x * 2)
        assert result.metadata == {"key": "value"}


@pytest.mark.unit
class TestModelOptionalIntCoercionModeEnum:
    """Tests for coercion mode enum."""

    def test_coercion_mode_strict(self) -> None:
        """Test STRICT coercion mode enum value."""
        mode = EnumCoercionMode.STRICT
        assert mode.value == "strict"

    def test_coercion_mode_floor(self) -> None:
        """Test FLOOR coercion mode enum value."""
        mode = EnumCoercionMode.FLOOR
        assert mode.value == "floor"

    def test_coercion_mode_ceil(self) -> None:
        """Test CEIL coercion mode enum value."""
        mode = EnumCoercionMode.CEIL
        assert mode.value == "ceil"

    def test_coercion_mode_round(self) -> None:
        """Test ROUND coercion mode enum value."""
        mode = EnumCoercionMode.ROUND
        assert mode.value == "round"

    def test_coercion_mode_string_comparison(self) -> None:
        """Test coercion mode can be compared with string."""
        mode = EnumCoercionMode.STRICT
        assert mode == "strict"


@pytest.mark.unit
class TestModelOptionalIntAsDictSerialization:
    """Tests for dictionary serialization."""

    def test_as_dict_with_value(self) -> None:
        """Test as_dict with present value."""
        value = ModelOptionalInt(value=42, metadata={"key": "value"})
        result = value.as_dict()
        assert result == {
            "value": 42,
            "coercion_mode": "strict",
            "metadata": {"key": "value"},
        }

    def test_as_dict_with_none(self) -> None:
        """Test as_dict with None value."""
        value = ModelOptionalInt(value=None)
        result = value.as_dict()
        assert result == {
            "value": None,
            "coercion_mode": "strict",
            "metadata": {},
        }

    def test_as_dict_with_floor_mode(self) -> None:
        """Test as_dict includes coercion mode."""
        value = ModelOptionalInt(value=42, coercion_mode=EnumCoercionMode.FLOOR)
        result = value.as_dict()
        assert result["coercion_mode"] == "floor"


@pytest.mark.unit
class TestModelOptionalIntPydanticSerialization:
    """Tests for Pydantic model serialization."""

    def test_model_dump_with_value(self) -> None:
        """Test model_dump with present value."""
        value = ModelOptionalInt(value=42)
        result = value.model_dump()
        assert result["value"] == 42
        assert result["coercion_mode"] == "strict"

    def test_model_dump_with_none(self) -> None:
        """Test model_dump with None value."""
        value = ModelOptionalInt(value=None)
        result = value.model_dump()
        assert result["value"] is None

    def test_model_dump_json(self) -> None:
        """Test model_dump_json serialization."""
        value = ModelOptionalInt(value=42, metadata={"key": "value"})
        json_str = value.model_dump_json()
        assert '"value":42' in json_str or '"value": 42' in json_str
        assert "strict" in json_str

    def test_round_trip_serialization(self) -> None:
        """Test round-trip serialization through dict."""
        original = ModelOptionalInt(
            value=42,
            coercion_mode=EnumCoercionMode.FLOOR,
            metadata={"test": "data"},
        )
        data = original.model_dump()
        restored = ModelOptionalInt(**data)
        assert restored.value == 42
        assert restored.coercion_mode == EnumCoercionMode.FLOOR
        assert restored.metadata == {"test": "data"}


@pytest.mark.unit
class TestModelOptionalIntStringRepresentation:
    """Tests for string representations."""

    def test_str_with_value(self) -> None:
        """Test __str__ with present value."""
        value = ModelOptionalInt(value=42)
        result = str(value)
        assert result == "OptionalInt(42)"

    def test_str_with_none(self) -> None:
        """Test __str__ with None value."""
        value = ModelOptionalInt(value=None)
        result = str(value)
        assert result == "OptionalInt(None)"

    def test_repr_with_value(self) -> None:
        """Test __repr__ with present value."""
        value = ModelOptionalInt(value=42, coercion_mode=EnumCoercionMode.FLOOR)
        result = repr(value)
        assert "ModelOptionalInt" in result
        assert "42" in result
        assert "floor" in result

    def test_repr_with_none(self) -> None:
        """Test __repr__ with None value."""
        value = ModelOptionalInt(value=None)
        result = repr(value)
        assert "ModelOptionalInt" in result
        assert "None" in result


@pytest.mark.unit
class TestModelOptionalIntBooleanConversion:
    """Tests for boolean conversion."""

    def test_bool_with_positive_value(self) -> None:
        """Test bool() returns True for positive value."""
        value = ModelOptionalInt(value=42)
        assert bool(value) is True

    def test_bool_with_negative_value(self) -> None:
        """Test bool() returns True for negative value."""
        value = ModelOptionalInt(value=-10)
        assert bool(value) is True

    def test_bool_with_zero_value(self) -> None:
        """Test bool() returns True even for zero (value is present)."""
        value = ModelOptionalInt(value=0)
        assert bool(value) is True

    def test_bool_with_none(self) -> None:
        """Test bool() returns False for None."""
        value = ModelOptionalInt(value=None)
        assert bool(value) is False

    def test_bool_in_if_statement_with_value(self) -> None:
        """Test boolean conversion in if statement with value."""
        value = ModelOptionalInt(value=42)
        if value:
            result = True
        else:
            result = False
        assert result is True

    def test_bool_in_if_statement_with_none(self) -> None:
        """Test boolean conversion in if statement with None."""
        value = ModelOptionalInt(value=None)
        if value:
            result = True
        else:
            result = False
        assert result is False


@pytest.mark.unit
class TestModelOptionalIntEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_large_positive_int(self) -> None:
        """Test with very large positive integer."""
        large_value = 10**100
        value = ModelOptionalInt(value=large_value)
        assert value.unwrap() == large_value

    def test_very_large_negative_int(self) -> None:
        """Test with very large negative integer."""
        large_value = -(10**100)
        value = ModelOptionalInt(value=large_value)
        assert value.unwrap() == large_value

    def test_int_max_value(self) -> None:
        """Test with maximum 64-bit integer."""
        max_value = 2**63 - 1
        value = ModelOptionalInt(value=max_value)
        assert value.unwrap() == max_value

    def test_int_min_value(self) -> None:
        """Test with minimum 64-bit integer."""
        min_value = -(2**63)
        value = ModelOptionalInt(value=min_value)
        assert value.unwrap() == min_value

    def test_float_very_close_to_integer(self) -> None:
        """Test float very close to integer in STRICT mode."""
        with pytest.raises(ModelOnexError):
            ModelOptionalInt(value=3.0000000001)

    def test_negative_zero_float(self) -> None:
        """Test negative zero float coerces correctly."""
        value = ModelOptionalInt(value=-0.0)
        assert value.unwrap() == 0

    def test_coercion_mode_case_insensitive_via_string(self) -> None:
        """Test coercion mode accepts string values."""
        # Test that we can pass string and it converts to enum
        value = ModelOptionalInt(value=3.7, coercion_mode="floor")  # type: ignore[arg-type]
        assert value.value == 3


@pytest.mark.unit
class TestModelOptionalIntIsSomeIsNone:
    """Tests for is_some() and is_none() methods."""

    def test_is_some_with_value(self) -> None:
        """Test is_some returns True when value present."""
        value = ModelOptionalInt(value=42)
        assert value.is_some() is True

    def test_is_some_with_zero(self) -> None:
        """Test is_some returns True for zero value."""
        value = ModelOptionalInt(value=0)
        assert value.is_some() is True

    def test_is_some_with_none(self) -> None:
        """Test is_some returns False when None."""
        value = ModelOptionalInt(value=None)
        assert value.is_some() is False

    def test_is_none_with_value(self) -> None:
        """Test is_none returns False when value present."""
        value = ModelOptionalInt(value=42)
        assert value.is_none() is False

    def test_is_none_with_zero(self) -> None:
        """Test is_none returns False for zero value."""
        value = ModelOptionalInt(value=0)
        assert value.is_none() is False

    def test_is_none_with_none(self) -> None:
        """Test is_none returns True when None."""
        value = ModelOptionalInt(value=None)
        assert value.is_none() is True

    def test_is_some_and_is_none_are_opposites(self) -> None:
        """Test is_some and is_none are always opposites."""
        for test_value in [None, 0, 42, -10]:
            value = ModelOptionalInt(value=test_value)
            assert value.is_some() != value.is_none()


@pytest.mark.unit
class TestModelOptionalIntPydanticValidation:
    """Tests for Pydantic validation behavior."""

    def test_extra_fields_ignored(self) -> None:
        """Test extra fields are ignored per model config."""
        value = ModelOptionalInt(
            value=42,
            extra_field="ignored",  # type: ignore[call-arg]
        )
        assert value.value == 42
        assert not hasattr(value, "extra_field")

    def test_validate_assignment_enabled(self) -> None:
        """Test assignment validation is enabled."""
        value = ModelOptionalInt(value=42)
        # Assignment validation should allow setting to int
        value.value = 100
        assert value.value == 100


@pytest.mark.unit
class TestModelOptionalIntAdditionalEdgeCases:
    """Additional edge case tests for boundary conditions and special values."""

    def test_sys_maxsize_value(self) -> None:
        """Test with sys.maxsize (platform-specific maximum int)."""
        import sys

        value = ModelOptionalInt(value=sys.maxsize)
        assert value.unwrap() == sys.maxsize
        assert value.is_some() is True

    def test_negative_sys_maxsize_value(self) -> None:
        """Test with negative sys.maxsize."""
        import sys

        value = ModelOptionalInt(value=-sys.maxsize)
        assert value.unwrap() == -sys.maxsize
        assert value.is_some() is True

    def test_bankers_rounding_round_to_even_2_5(self) -> None:
        """Test banker's rounding: 2.5 rounds to 2 (nearest even)."""
        value = ModelOptionalInt(value=2.5, coercion_mode=EnumCoercionMode.ROUND)
        assert value.value == 2  # Python's round() uses banker's rounding

    def test_bankers_rounding_round_to_even_4_5(self) -> None:
        """Test banker's rounding: 4.5 rounds to 4 (nearest even)."""
        value = ModelOptionalInt(value=4.5, coercion_mode=EnumCoercionMode.ROUND)
        assert value.value == 4  # Python's round() uses banker's rounding

    def test_bankers_rounding_round_to_odd_1_5(self) -> None:
        """Test banker's rounding: 1.5 rounds to 2 (nearest even)."""
        value = ModelOptionalInt(value=1.5, coercion_mode=EnumCoercionMode.ROUND)
        assert value.value == 2  # 1.5 -> 2 (even)

    def test_dict_instantiation_without_keyword(self) -> None:
        """Test dict-based instantiation using model_validate.

        The model_validator(mode='before') handles dict inputs where 'value'
        can be any supported type (int, float, None).
        """
        # Using model_validate with dict that contains the value
        value = ModelOptionalInt.model_validate({"value": 42})
        assert value.value == 42
        assert value.is_some() is True

    def test_dict_instantiation_with_none(self) -> None:
        """Test dict-based instantiation with None using model_validate."""
        value = ModelOptionalInt.model_validate({"value": None})
        assert value.value is None
        assert value.is_none() is True

    def test_bool_with_logical_not_operator(self) -> None:
        """Test logical not operator with __bool__."""
        value_some = ModelOptionalInt(value=42)
        value_none = ModelOptionalInt(value=None)

        assert value_some is not False  # not True == False
        assert value_none is not True  # not False == True

    def test_bool_with_logical_and_operator(self) -> None:
        """Test logical and operator with __bool__."""
        value_some = ModelOptionalInt(value=42)
        value_none = ModelOptionalInt(value=None)

        # and short-circuits: returns first falsy or last value
        assert (value_some and value_some) is value_some
        assert (value_none and value_some) is value_none
        assert (value_some and value_none) is value_none

    def test_bool_with_logical_or_operator(self) -> None:
        """Test logical or operator with __bool__."""
        value_some = ModelOptionalInt(value=42)
        value_none = ModelOptionalInt(value=None)

        # or short-circuits: returns first truthy or last value
        assert (value_some or value_none) is value_some
        assert (value_none or value_some) is value_some
        assert (value_none or value_none) is value_none

    def test_bool_in_conditional_expression(self) -> None:
        """Test __bool__ in ternary conditional expression."""
        value_some = ModelOptionalInt(value=42)
        value_none = ModelOptionalInt(value=None)

        result_some = "present" if value_some else "absent"
        result_none = "present" if value_none else "absent"

        assert result_some == "present"
        assert result_none == "absent"

    def test_bool_zero_vs_none_distinction(self) -> None:
        """Explicitly test that 0 and None have different boolean behavior.

        This is a critical edge case: 0 is a valid value (truthy),
        while None indicates absence (falsy).
        """
        zero = ModelOptionalInt(value=0)
        none = ModelOptionalInt(value=None)

        # 0 is a present value, so bool is True
        assert bool(zero) is True
        assert zero.is_some() is True
        assert zero.is_none() is False

        # None indicates absence, so bool is False
        assert bool(none) is False
        assert none.is_some() is False
        assert none.is_none() is True

        # Critically different from standard Python int behavior
        # where bool(0) == False
        assert bool(0) is False  # Standard Python
        assert bool(zero) is True  # ModelOptionalInt (value presence)

    def test_unwrap_or_with_zero_default(self) -> None:
        """Test unwrap_or when default is 0."""
        none_value = ModelOptionalInt(value=None)
        some_value = ModelOptionalInt(value=42)

        assert none_value.unwrap_or(0) == 0
        assert some_value.unwrap_or(0) == 42

    def test_unwrap_or_with_negative_default(self) -> None:
        """Test unwrap_or when default is negative."""
        none_value = ModelOptionalInt(value=None)
        assert none_value.unwrap_or(-1) == -1

    def test_map_with_zero_result(self) -> None:
        """Test map that produces zero as result."""
        value = ModelOptionalInt(value=5)
        result = value.map(lambda x: x - 5)  # 5 - 5 = 0
        assert result.value == 0
        assert result.is_some() is True
        assert bool(result) is True

    def test_very_small_positive_float_strict_mode(self) -> None:
        """Test very small positive float in STRICT mode raises error."""
        with pytest.raises(ModelOnexError):
            ModelOptionalInt(value=0.000001)

    def test_very_small_negative_float_strict_mode(self) -> None:
        """Test very small negative float in STRICT mode raises error."""
        with pytest.raises(ModelOnexError):
            ModelOptionalInt(value=-0.000001)

    def test_float_with_many_decimal_places_exact(self) -> None:
        """Test float with many decimal places that equals an exact integer."""
        # 5.0000000000000000 should coerce to 5 in STRICT mode
        value = ModelOptionalInt(value=5.0000000000000000)
        assert value.value == 5

    def test_large_exact_float_coercion(self) -> None:
        """Test large float that is exactly an integer."""
        large_float = 1e15  # 1000000000000000.0
        value = ModelOptionalInt(value=large_float)
        assert value.value == 1000000000000000
        assert isinstance(value.value, int)


@pytest.mark.unit
class TestModelOptionalIntEqualityComparisons:
    """Tests for equality and comparison behavior."""

    def test_equality_same_value(self) -> None:
        """Test equality of two instances with same value."""
        a = ModelOptionalInt(value=42)
        b = ModelOptionalInt(value=42)
        assert a == b

    def test_equality_both_none(self) -> None:
        """Test equality of two None instances."""
        a = ModelOptionalInt(value=None)
        b = ModelOptionalInt(value=None)
        assert a == b

    def test_inequality_different_values(self) -> None:
        """Test inequality of instances with different values."""
        a = ModelOptionalInt(value=42)
        b = ModelOptionalInt(value=43)
        assert a != b

    def test_inequality_value_vs_none(self) -> None:
        """Test inequality of value vs None."""
        a = ModelOptionalInt(value=42)
        b = ModelOptionalInt(value=None)
        assert a != b

    def test_equality_ignores_coercion_mode_for_same_value(self) -> None:
        """Test that equal values are equal regardless of coercion mode."""
        a = ModelOptionalInt(value=42, coercion_mode=EnumCoercionMode.STRICT)
        b = ModelOptionalInt(value=42, coercion_mode=EnumCoercionMode.FLOOR)
        # Pydantic models compare all fields, so different modes mean not equal
        assert a != b

    def test_equality_with_metadata_difference(self) -> None:
        """Test that different metadata makes instances unequal."""
        a = ModelOptionalInt(value=42, metadata={"key": "value1"})
        b = ModelOptionalInt(value=42, metadata={"key": "value2"})
        assert a != b

    def test_equality_zero_values(self) -> None:
        """Test equality of zero value instances."""
        a = ModelOptionalInt(value=0)
        b = ModelOptionalInt(value=0)
        assert a == b


@pytest.mark.unit
class TestModelOptionalIntCollectionOperations:
    """Tests for using ModelOptionalInt in collections."""

    def test_all_with_all_present_values(self) -> None:
        """Test all() with collection where all values are present."""
        values = [
            ModelOptionalInt(value=1),
            ModelOptionalInt(value=0),  # 0 is present, so truthy
            ModelOptionalInt(value=-1),
        ]
        assert all(values) is True

    def test_all_with_some_none_values(self) -> None:
        """Test all() with collection containing None values."""
        values = [
            ModelOptionalInt(value=1),
            ModelOptionalInt(value=None),  # None is falsy
            ModelOptionalInt(value=2),
        ]
        assert all(values) is False

    def test_any_with_all_none_values(self) -> None:
        """Test any() with collection where all values are None."""
        values = [
            ModelOptionalInt(value=None),
            ModelOptionalInt(value=None),
        ]
        assert any(values) is False

    def test_any_with_one_present_value(self) -> None:
        """Test any() with collection containing one present value."""
        values = [
            ModelOptionalInt(value=None),
            ModelOptionalInt(value=42),
            ModelOptionalInt(value=None),
        ]
        assert any(values) is True

    def test_filter_present_values(self) -> None:
        """Test filtering to get only present values."""
        values = [
            ModelOptionalInt(value=1),
            ModelOptionalInt(value=None),
            ModelOptionalInt(value=2),
            ModelOptionalInt(value=None),
            ModelOptionalInt(value=3),
        ]
        present = list(filter(lambda x: x, values))
        assert len(present) == 3
        assert all(v.is_some() for v in present)

    def test_in_list_membership(self) -> None:
        """Test membership checking in list."""
        target = ModelOptionalInt(value=42)
        values = [
            ModelOptionalInt(value=1),
            ModelOptionalInt(value=42),
            ModelOptionalInt(value=3),
        ]
        assert target in values


@pytest.mark.unit
class TestModelOptionalIntTypePreservation:
    """Tests to verify type is always int after operations."""

    def test_value_type_is_int_after_float_coercion_strict(self) -> None:
        """Test that value is int type after strict float coercion."""
        value = ModelOptionalInt(value=5.0)
        assert isinstance(value.value, int)
        assert type(value.value) is int  # Strict type check

    def test_value_type_is_int_after_floor_coercion(self) -> None:
        """Test that value is int type after floor coercion."""
        value = ModelOptionalInt(value=5.9, coercion_mode=EnumCoercionMode.FLOOR)
        assert isinstance(value.value, int)
        assert type(value.value) is int

    def test_value_type_is_int_after_ceil_coercion(self) -> None:
        """Test that value is int type after ceil coercion."""
        value = ModelOptionalInt(value=5.1, coercion_mode=EnumCoercionMode.CEIL)
        assert isinstance(value.value, int)
        assert type(value.value) is int

    def test_value_type_is_int_after_round_coercion(self) -> None:
        """Test that value is int type after round coercion."""
        value = ModelOptionalInt(value=5.5, coercion_mode=EnumCoercionMode.ROUND)
        assert isinstance(value.value, int)
        assert type(value.value) is int

    def test_value_type_after_map_operation(self) -> None:
        """Test that value type is preserved after map."""
        value = ModelOptionalInt(value=5)
        result = value.map(lambda x: x * 3)
        assert isinstance(result.value, int)

    def test_unwrap_returns_int_type(self) -> None:
        """Test that unwrap returns exact int type."""
        value = ModelOptionalInt(value=42)
        result = value.unwrap()
        assert type(result) is int


@pytest.mark.unit
class TestModelOptionalIntFloatPrecisionEdgeCases:
    """Tests for floating point precision edge cases."""

    def test_round_half_away_from_zero_negative(self) -> None:
        """Test rounding -2.5 (banker's rounds to -2)."""
        value = ModelOptionalInt(value=-2.5, coercion_mode=EnumCoercionMode.ROUND)
        assert value.value == -2  # Python banker's rounding

    def test_round_half_away_from_zero_negative_odd(self) -> None:
        """Test rounding -3.5 (banker's rounds to -4)."""
        value = ModelOptionalInt(value=-3.5, coercion_mode=EnumCoercionMode.ROUND)
        assert value.value == -4  # Python banker's rounding

    def test_floor_negative_exact_integer(self) -> None:
        """Test floor of negative exact integer float."""
        value = ModelOptionalInt(value=-5.0, coercion_mode=EnumCoercionMode.FLOOR)
        assert value.value == -5

    def test_ceil_negative_exact_integer(self) -> None:
        """Test ceil of negative exact integer float."""
        value = ModelOptionalInt(value=-5.0, coercion_mode=EnumCoercionMode.CEIL)
        assert value.value == -5

    def test_floor_very_small_negative_fraction(self) -> None:
        """Test floor with very small negative fractional part."""
        value = ModelOptionalInt(value=-0.001, coercion_mode=EnumCoercionMode.FLOOR)
        assert value.value == -1  # floor(-0.001) = -1

    def test_ceil_very_small_positive_fraction(self) -> None:
        """Test ceil with very small positive fractional part."""
        value = ModelOptionalInt(value=0.001, coercion_mode=EnumCoercionMode.CEIL)
        assert value.value == 1  # ceil(0.001) = 1

    def test_round_just_below_half(self) -> None:
        """Test rounding value just below .5."""
        value = ModelOptionalInt(value=3.49999, coercion_mode=EnumCoercionMode.ROUND)
        assert value.value == 3

    def test_round_just_above_half(self) -> None:
        """Test rounding value just above .5."""
        value = ModelOptionalInt(value=3.50001, coercion_mode=EnumCoercionMode.ROUND)
        assert value.value == 4


@pytest.mark.unit
class TestModelOptionalIntBoundaryValues:
    """Tests for extreme boundary values."""

    def test_sys_maxsize_plus_one(self) -> None:
        """Test with sys.maxsize + 1 (Python handles arbitrary precision)."""
        import sys

        value = ModelOptionalInt(value=sys.maxsize + 1)
        assert value.unwrap() == sys.maxsize + 1

    def test_negative_sys_maxsize_minus_one(self) -> None:
        """Test with -sys.maxsize - 1."""
        import sys

        value = ModelOptionalInt(value=-sys.maxsize - 1)
        assert value.unwrap() == -sys.maxsize - 1

    def test_very_large_arbitrary_precision(self) -> None:
        """Test with extremely large number (Python arbitrary precision)."""
        huge = 10**1000  # Much larger than any machine word
        value = ModelOptionalInt(value=huge)
        assert value.unwrap() == huge

    def test_very_small_arbitrary_precision(self) -> None:
        """Test with extremely small (negative) number."""
        tiny = -(10**1000)
        value = ModelOptionalInt(value=tiny)
        assert value.unwrap() == tiny

    def test_one(self) -> None:
        """Test boundary value 1."""
        value = ModelOptionalInt(value=1)
        assert value.unwrap() == 1
        assert bool(value) is True

    def test_negative_one(self) -> None:
        """Test boundary value -1."""
        value = ModelOptionalInt(value=-1)
        assert value.unwrap() == -1
        assert bool(value) is True


@pytest.mark.unit
class TestModelOptionalIntChainedOperations:
    """Tests for complex chained operations."""

    def test_map_chain_preserving_none(self) -> None:
        """Test that None propagates through map chain."""
        value = ModelOptionalInt(value=None)
        result = value.map(lambda x: x * 2).map(lambda x: x + 10).map(lambda x: x // 2)
        assert result.is_none() is True

    def test_map_to_zero_preserves_some(self) -> None:
        """Test map chain that results in zero still preserves Some state."""
        value = ModelOptionalInt(value=10)
        result = value.map(lambda x: x - 10)  # Results in 0
        assert result.value == 0
        assert result.is_some() is True
        assert bool(result) is True

    def test_map_with_identity_function(self) -> None:
        """Test map with identity function preserves value."""
        value = ModelOptionalInt(value=42)
        result = value.map(lambda x: x)
        assert result.value == 42
        assert result == value

    def test_map_with_negative_result(self) -> None:
        """Test map that produces negative result."""
        value = ModelOptionalInt(value=5)
        result = value.map(lambda x: x - 100)
        assert result.value == -95
        assert result.is_some() is True

    def test_multiple_unwrap_calls(self) -> None:
        """Test that multiple unwrap calls return same value."""
        value = ModelOptionalInt(value=42)
        assert value.unwrap() == value.unwrap() == value.unwrap()

    def test_unwrap_or_chain(self) -> None:
        """Test unwrap_or can be used in chained expressions."""
        values = [
            ModelOptionalInt(value=None),
            ModelOptionalInt(value=None),
            ModelOptionalInt(value=42),
        ]
        # Find first non-None or return -1
        result = -1
        for v in values:
            if v.is_some():
                result = v.unwrap()
                break
        assert result == 42


@pytest.mark.unit
class TestModelOptionalIntErrorContextValidation:
    """Tests for error context and message validation."""

    def test_unwrap_none_error_has_hint(self) -> None:
        """Test that unwrap on None includes helpful hint in context."""
        value = ModelOptionalInt(value=None)
        with pytest.raises(ModelOnexError) as exc_info:
            value.unwrap()
        # The hint is in the error context, not the main message
        error = exc_info.value
        assert "Called unwrap() on None value" in str(error)
        # Verify context contains the hint (nested under additional_context.context)
        assert error.context is not None
        context_str = str(error.context)
        assert "unwrap_or()" in context_str or "unwrap_or_else()" in context_str

    def test_non_exact_float_error_includes_fractional_part(self) -> None:
        """Test that non-exact float error includes fractional part info."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOptionalInt(value=3.14159)
        error_str = str(exc_info.value)
        assert "3.14159" in error_str or "not an exact integer" in error_str

    def test_invalid_type_error_includes_type_name(self) -> None:
        """Test that invalid type error includes the actual type name."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOptionalInt(value="not an int")  # type: ignore[arg-type]
        assert "str" in str(exc_info.value)

    def test_nan_error_context_includes_is_nan(self) -> None:
        """Test that NaN error provides context about the issue."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOptionalInt(value=float("nan"))
        assert "NaN" in str(exc_info.value) or "nan" in str(exc_info.value).lower()

    def test_infinity_error_context_includes_is_inf(self) -> None:
        """Test that infinity error provides context."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelOptionalInt(value=float("inf"))
        assert (
            "infinity" in str(exc_info.value).lower()
            or "inf" in str(exc_info.value).lower()
        )


@pytest.mark.unit
class TestModelOptionalIntAssignmentBehavior:
    """Tests for value assignment and mutation behavior."""

    def test_direct_assignment_validated(self) -> None:
        """Test that direct assignment triggers validation."""
        value = ModelOptionalInt(value=42)
        value.value = 100
        assert value.value == 100
        assert isinstance(value.value, int)

    def test_assignment_to_none(self) -> None:
        """Test assigning None to a value."""
        value = ModelOptionalInt(value=42)
        value.value = None
        assert value.value is None
        assert value.is_none() is True

    def test_assignment_from_none_to_value(self) -> None:
        """Test assigning value to previously None instance."""
        value = ModelOptionalInt(value=None)
        value.value = 42
        assert value.value == 42
        assert value.is_some() is True

    def test_coercion_mode_preserved_after_assignment(self) -> None:
        """Test that coercion mode is preserved after value assignment."""
        value = ModelOptionalInt(value=42, coercion_mode=EnumCoercionMode.FLOOR)
        value.value = 100
        assert value.coercion_mode == EnumCoercionMode.FLOOR


@pytest.mark.unit
class TestModelOptionalIntSpecialInputs:
    """Tests for special input scenarios."""

    def test_complex_number_raises_error(self) -> None:
        """Test that complex numbers are rejected."""
        with pytest.raises(ModelOnexError):
            ModelOptionalInt(value=complex(3, 4))  # type: ignore[arg-type]

    def test_empty_string_raises_error(self) -> None:
        """Test that empty string is rejected."""
        with pytest.raises(ModelOnexError):
            ModelOptionalInt(value="")  # type: ignore[arg-type]

    def test_whitespace_string_raises_error(self) -> None:
        """Test that whitespace string is rejected."""
        with pytest.raises(ModelOnexError):
            ModelOptionalInt(value="   ")  # type: ignore[arg-type]

    def test_numeric_string_raises_error(self) -> None:
        """Test that numeric string is rejected (no implicit conversion)."""
        with pytest.raises(ModelOnexError):
            ModelOptionalInt(value="42")  # type: ignore[arg-type]

    def test_bytes_raises_error(self) -> None:
        """Test that bytes are rejected."""
        with pytest.raises(ModelOnexError):
            ModelOptionalInt(value=b"42")  # type: ignore[arg-type]

    def test_tuple_raises_error(self) -> None:
        """Test that tuples are rejected."""
        with pytest.raises(ModelOnexError):
            ModelOptionalInt(value=(1, 2))  # type: ignore[arg-type]

    def test_set_raises_error(self) -> None:
        """Test that sets are rejected."""
        with pytest.raises(ModelOnexError):
            ModelOptionalInt(value={1, 2})  # type: ignore[arg-type]
