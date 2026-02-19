# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for model_typed_metadata.py - Type validation tests.

This module tests the type-default and type-enum consistency validation in
ModelConfigSchemaProperty, ensuring that 'default' and 'enum' values match
the declared 'type' field.

Test Categories (PR #180 Requirements):
1. Test that `default=3.5` with `type="integer"` raises error
2. Test that `default="text"` with `type="number"` raises error
3. Test that `default=42` with `type="string"` raises error
4. Test that enum values match the declared type
5. Additional edge cases for comprehensive coverage
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_typed_metadata import (
    ModelConfigSchemaProperty,
    ModelMixinConfigSchema,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# =============================================================================
# Type-Default Consistency Validation Tests
# =============================================================================


@pytest.mark.unit
class TestConfigSchemaPropertyTypeValidation:
    """Tests for type-default consistency validation in ModelConfigSchemaProperty.

    PR #180 Requirements:
    - Test that `default=3.5` with `type="integer"` raises error
    - Test that `default="text"` with `type="number"` raises error
    - Test that `default=42` with `type="string"` raises error
    """

    def test_float_default_with_integer_type_raises_error(self) -> None:
        """Test that default=3.5 with type='integer' raises validation error.

        PR #180 Requirement: Test that `default=3.5` with `type="integer"` raises error.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            ModelConfigSchemaProperty(
                type="integer",
                default=3.5,  # Float value for integer type
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "float" in str(exc_info.value.message).lower()
        assert "integer" in str(exc_info.value.message).lower()

    def test_string_default_with_number_type_raises_error(self) -> None:
        """Test that default='text' with type='number' raises validation error.

        PR #180 Requirement: Test that `default="text"` with `type="number"` raises error.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            ModelConfigSchemaProperty(
                type="number",
                default="text",  # String value for number type
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "str" in str(exc_info.value.message).lower()
        assert "number" in str(exc_info.value.message).lower()

    def test_integer_default_with_string_type_raises_error(self) -> None:
        """Test that default=42 with type='string' raises validation error.

        PR #180 Requirement: Test that `default=42` with `type="string"` raises error.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            ModelConfigSchemaProperty(
                type="string",
                default=42,  # Integer value for string type
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "int" in str(exc_info.value.message).lower()
        assert "string" in str(exc_info.value.message).lower()

    def test_bool_default_with_integer_type_raises_error(self) -> None:
        """Test that boolean default with integer type raises error.

        This tests the special case where bool is a subclass of int in Python,
        but we explicitly disallow bool values for integer types.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            ModelConfigSchemaProperty(
                type="integer",
                default=True,  # Bool value for integer type
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "bool" in str(exc_info.value.message).lower()

    def test_bool_default_with_number_type_raises_error(self) -> None:
        """Test that boolean default with number type raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelConfigSchemaProperty(
                type="number",
                default=False,  # Bool value for number type
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "bool" in str(exc_info.value.message).lower()

    def test_list_default_with_string_type_raises_error(self) -> None:
        """Test that list default with string type raises error.

        Note: Pydantic will reject list type before our validator runs since
        the field type is `str | int | float | bool | None`.
        """
        with pytest.raises((ModelOnexError, ValueError)):
            ModelConfigSchemaProperty(
                type="string",
                default=["item1", "item2"],  # type: ignore[arg-type]
                description="Test parameter",
            )


# =============================================================================
# Valid Type-Default Combinations Tests
# =============================================================================


@pytest.mark.unit
class TestConfigSchemaPropertyValidCombinations:
    """Tests for valid type-default combinations."""

    def test_valid_string_default_with_string_type_succeeds(self) -> None:
        """Test that valid string default with string type succeeds."""
        prop = ModelConfigSchemaProperty(
            type="string",
            default="hello",
            description="Test parameter",
        )
        assert prop.default == "hello"
        assert prop.type == "string"

    def test_valid_integer_default_with_integer_type_succeeds(self) -> None:
        """Test that valid integer default with integer type succeeds."""
        prop = ModelConfigSchemaProperty(
            type="integer",
            default=42,
            description="Test parameter",
        )
        assert prop.default == 42
        assert prop.type == "integer"

    def test_valid_float_default_with_float_type_succeeds(self) -> None:
        """Test that valid float default with float type succeeds."""
        prop = ModelConfigSchemaProperty(
            type="float",
            default=3.14,
            description="Test parameter",
        )
        assert prop.default == 3.14
        assert prop.type == "float"

    def test_valid_float_default_with_number_type_succeeds(self) -> None:
        """Test that valid float default with number type succeeds."""
        prop = ModelConfigSchemaProperty(
            type="number",
            default=3.14,
            description="Test parameter",
        )
        assert prop.default == 3.14
        assert prop.type == "number"

    def test_valid_bool_default_with_boolean_type_succeeds(self) -> None:
        """Test that valid boolean default with boolean type succeeds."""
        prop = ModelConfigSchemaProperty(
            type="boolean",
            default=True,
            description="Test parameter",
        )
        assert prop.default is True
        assert prop.type == "boolean"

    def test_int_acceptable_for_number_type(self) -> None:
        """Test that int is acceptable for number type (widening conversion)."""
        prop = ModelConfigSchemaProperty(
            type="number",
            default=42,  # Int is acceptable for number
            description="Test parameter",
        )
        assert prop.default == 42
        assert prop.type == "number"

    def test_int_acceptable_for_float_type(self) -> None:
        """Test that int is acceptable for float type (widening conversion)."""
        prop = ModelConfigSchemaProperty(
            type="float",
            default=42,  # Int is acceptable for float
            description="Test parameter",
        )
        assert prop.default == 42
        assert prop.type == "float"

    def test_none_default_is_always_valid(self) -> None:
        """Test that None default is valid for any type."""
        for type_name in ("string", "integer", "number", "boolean"):
            prop = ModelConfigSchemaProperty(
                type=type_name,
                default=None,
                description="Test parameter",
            )
            assert prop.default is None
            assert prop.type == type_name


# =============================================================================
# Type Alias Tests
# =============================================================================


@pytest.mark.unit
class TestConfigSchemaPropertyTypeAliases:
    """Tests for type alias handling (int, str, bool aliases)."""

    def test_str_alias_for_string_type(self) -> None:
        """Test that 'str' type alias works like 'string'."""
        prop = ModelConfigSchemaProperty(
            type="str",
            default="hello",
            description="Test parameter",
        )
        assert prop.default == "hello"

        with pytest.raises(ModelOnexError):
            ModelConfigSchemaProperty(
                type="str",
                default=42,  # Wrong type
                description="Test parameter",
            )

    def test_int_alias_for_integer_type(self) -> None:
        """Test that 'int' type alias works like 'integer'."""
        prop = ModelConfigSchemaProperty(
            type="int",
            default=42,
            description="Test parameter",
        )
        assert prop.default == 42

        with pytest.raises(ModelOnexError):
            ModelConfigSchemaProperty(
                type="int",
                default=3.14,  # Wrong type
                description="Test parameter",
            )

    def test_bool_alias_for_boolean_type(self) -> None:
        """Test that 'bool' type alias works like 'boolean'."""
        prop = ModelConfigSchemaProperty(
            type="bool",
            default=False,
            description="Test parameter",
        )
        assert prop.default is False

        with pytest.raises(ModelOnexError):
            ModelConfigSchemaProperty(
                type="bool",
                default="true",  # Wrong type (string, not bool)
                description="Test parameter",
            )


# =============================================================================
# Unknown Type Tests
# =============================================================================


@pytest.mark.unit
class TestConfigSchemaPropertyUnknownTypes:
    """Tests for unknown/custom type handling."""

    def test_unknown_type_allows_any_default(self) -> None:
        """Test that unknown types don't trigger validation.

        Types like 'array', 'object', or custom types skip type validation
        since we don't have a mapping for them.
        """
        # 'array' type with various defaults
        prop1 = ModelConfigSchemaProperty(
            type="array",
            default="some_value",
            description="Test parameter",
        )
        assert prop1.default == "some_value"

        # 'object' type with various defaults
        prop2 = ModelConfigSchemaProperty(
            type="object",
            default=42,
            description="Test parameter",
        )
        assert prop2.default == 42

        # Custom type
        prop3 = ModelConfigSchemaProperty(
            type="custom_type",
            default=True,
            description="Test parameter",
        )
        assert prop3.default is True


# =============================================================================
# ModelMixinConfigSchema Integration Tests
# =============================================================================


@pytest.mark.unit
class TestMixinConfigSchemaIntegration:
    """Tests for ModelMixinConfigSchema with type validation."""

    def test_schema_with_valid_properties(self) -> None:
        """Test creating schema with valid property type-default combinations."""
        schema = ModelMixinConfigSchema(
            properties={
                "name": ModelConfigSchemaProperty(
                    type="string",
                    default="default_name",
                    description="Name parameter",
                ),
                "count": ModelConfigSchemaProperty(
                    type="integer",
                    default=10,
                    description="Count parameter",
                ),
                "enabled": ModelConfigSchemaProperty(
                    type="boolean",
                    default=True,
                    description="Enabled flag",
                ),
            },
            required_properties=["name"],
        )

        assert len(schema.properties) == 3
        assert schema.properties["name"].default == "default_name"
        assert schema.properties["count"].default == 10
        assert schema.properties["enabled"].default is True

    def test_schema_with_invalid_property_raises_error(self) -> None:
        """Test that schema creation fails with invalid property type-default."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelMixinConfigSchema(
                properties={
                    "bad_param": ModelConfigSchemaProperty(
                        type="integer",
                        default="not_an_integer",  # Invalid!
                        description="Bad parameter",
                    ),
                },
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH


# =============================================================================
# Error Context Tests
# =============================================================================


@pytest.mark.unit
class TestConfigSchemaPropertyErrorContext:
    """Tests for error context information in type validation errors."""

    def test_error_context_contains_type_info(self) -> None:
        """Test that error context contains declared and actual type info."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelConfigSchemaProperty(
                type="integer",
                default=3.5,
                description="Test parameter",
            )

        context = exc_info.value.context
        assert context is not None
        # Context is nested under additional_context.context
        inner_context = context.get("additional_context", {}).get("context", {})
        assert inner_context.get("declared_type") == "integer"
        assert inner_context.get("actual_type") == "float"
        assert inner_context.get("default_value") == "3.5"

    def test_error_context_contains_default_value(self) -> None:
        """Test that error context contains the actual default value."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelConfigSchemaProperty(
                type="string",
                default=42,
                description="Test parameter",
            )

        context = exc_info.value.context
        assert context is not None
        # Context is nested under additional_context.context
        inner_context = context.get("additional_context", {}).get("context", {})
        assert inner_context.get("default_value") == "42"


# =============================================================================
# Enum Type Validation Tests
# =============================================================================


@pytest.mark.unit
class TestConfigSchemaPropertyEnumValidation:
    """Tests for type-enum consistency validation in ModelConfigSchemaProperty.

    PR #180 Requirements:
    - Test that enum values match the declared type
    - Test that mixed-type enum values raise errors when they don't match declared type
    """

    def test_string_enum_with_integer_type_raises_error(self) -> None:
        """Test that string enum values with integer type raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelConfigSchemaProperty(
                type="integer",
                enum=["low", "medium", "high"],  # String values for integer type
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "str" in str(exc_info.value.message).lower()
        assert "integer" in str(exc_info.value.message).lower()

    def test_integer_enum_with_string_type_raises_error(self) -> None:
        """Test that integer enum values with string type raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelConfigSchemaProperty(
                type="string",
                enum=[1, 2, 3],  # Integer values for string type
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "int" in str(exc_info.value.message).lower()
        assert "string" in str(exc_info.value.message).lower()

    def test_float_enum_with_integer_type_raises_error(self) -> None:
        """Test that float enum values with integer type raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelConfigSchemaProperty(
                type="integer",
                enum=[1.5, 2.5, 3.5],  # Float values for integer type
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "float" in str(exc_info.value.message).lower()
        assert "integer" in str(exc_info.value.message).lower()

    def test_bool_enum_with_integer_type_raises_error(self) -> None:
        """Test that boolean enum values with integer type raises error.

        This tests the special case where bool is a subclass of int in Python,
        but we explicitly disallow bool values for integer types.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            ModelConfigSchemaProperty(
                type="integer",
                enum=[True, False],  # Bool values for integer type
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "bool" in str(exc_info.value.message).lower()

    def test_bool_enum_with_number_type_raises_error(self) -> None:
        """Test that boolean enum values with number type raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelConfigSchemaProperty(
                type="number",
                enum=[True, False],  # Bool values for number type
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "bool" in str(exc_info.value.message).lower()

    def test_mixed_enum_with_first_invalid_raises_error(self) -> None:
        """Test that mixed enum with first invalid value raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelConfigSchemaProperty(
                type="string",
                enum=[42, "valid", "also_valid"],  # First value is invalid
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        # Error should be for enum[0]
        assert "enum[0]" in str(exc_info.value.message)

    def test_mixed_enum_with_later_invalid_raises_error(self) -> None:
        """Test that mixed enum with later invalid value raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelConfigSchemaProperty(
                type="string",
                enum=["valid", "also_valid", 42],  # Third value is invalid
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        # Error should be for enum[2]
        assert "enum[2]" in str(exc_info.value.message)

    def test_enum_context_contains_index(self) -> None:
        """Test that enum validation error context contains the enum index."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelConfigSchemaProperty(
                type="integer",
                enum=[1, 2, "invalid", 4],  # Third value (index 2) is invalid
                description="Test parameter",
            )

        context = exc_info.value.context
        assert context is not None
        inner_context = context.get("additional_context", {}).get("context", {})
        assert inner_context.get("enum_index") == 2


# =============================================================================
# Valid Enum Combinations Tests
# =============================================================================


@pytest.mark.unit
class TestConfigSchemaPropertyValidEnumCombinations:
    """Tests for valid type-enum combinations."""

    def test_valid_string_enum_with_string_type(self) -> None:
        """Test that valid string enum values with string type succeeds."""
        prop = ModelConfigSchemaProperty(
            type="string",
            enum=["low", "medium", "high"],
            description="Test parameter",
        )
        assert prop.enum == ["low", "medium", "high"]
        assert prop.type == "string"

    def test_valid_integer_enum_with_integer_type(self) -> None:
        """Test that valid integer enum values with integer type succeeds."""
        prop = ModelConfigSchemaProperty(
            type="integer",
            enum=[1, 2, 3, 4, 5],
            description="Test parameter",
        )
        assert prop.enum == [1, 2, 3, 4, 5]
        assert prop.type == "integer"

    def test_valid_float_enum_with_number_type(self) -> None:
        """Test that valid float enum values with number type succeeds."""
        prop = ModelConfigSchemaProperty(
            type="number",
            enum=[0.1, 0.5, 1.0, 2.0],
            description="Test parameter",
        )
        assert prop.enum == [0.1, 0.5, 1.0, 2.0]
        assert prop.type == "number"

    def test_valid_int_enum_with_number_type(self) -> None:
        """Test that int enum values are acceptable for number type (widening)."""
        prop = ModelConfigSchemaProperty(
            type="number",
            enum=[1, 2, 3],  # Ints are valid for number type
            description="Test parameter",
        )
        assert prop.enum == [1, 2, 3]
        assert prop.type == "number"

    def test_valid_mixed_int_float_enum_with_number_type(self) -> None:
        """Test that mixed int/float enum values are acceptable for number type."""
        prop = ModelConfigSchemaProperty(
            type="number",
            enum=[1, 2.5, 3, 4.0],  # Mixed ints and floats for number
            description="Test parameter",
        )
        assert prop.enum == [1, 2.5, 3, 4.0]
        assert prop.type == "number"

    def test_valid_bool_enum_with_boolean_type(self) -> None:
        """Test that valid boolean enum values with boolean type succeeds."""
        prop = ModelConfigSchemaProperty(
            type="boolean",
            enum=[True, False],
            description="Test parameter",
        )
        assert prop.enum == [True, False]
        assert prop.type == "boolean"

    def test_enum_with_none_values_allowed(self) -> None:
        """Test that None values in enum are allowed regardless of type."""
        prop = ModelConfigSchemaProperty(
            type="string",
            enum=["value1", None, "value2"],  # None is valid in any enum
            description="Test parameter",
        )
        assert prop.enum == ["value1", None, "value2"]

    def test_none_enum_is_valid(self) -> None:
        """Test that None enum field is valid (no enum constraint)."""
        prop = ModelConfigSchemaProperty(
            type="string",
            enum=None,
            description="Test parameter",
        )
        assert prop.enum is None

    def test_empty_enum_is_valid(self) -> None:
        """Test that empty enum list is valid."""
        prop = ModelConfigSchemaProperty(
            type="string",
            enum=[],
            description="Test parameter",
        )
        assert prop.enum == []


# =============================================================================
# Combined Default and Enum Validation Tests
# =============================================================================


@pytest.mark.unit
class TestConfigSchemaPropertyCombinedValidation:
    """Tests for combined default and enum validation."""

    def test_valid_default_and_enum_succeeds(self) -> None:
        """Test that valid default and enum with matching types succeeds."""
        prop = ModelConfigSchemaProperty(
            type="integer",
            default=1,
            enum=[1, 2, 3, 4, 5],
            description="Test parameter",
        )
        assert prop.default == 1
        assert prop.enum == [1, 2, 3, 4, 5]

    def test_invalid_default_with_valid_enum_raises_error(self) -> None:
        """Test that invalid default raises error even with valid enum."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelConfigSchemaProperty(
                type="integer",
                default=3.5,  # Invalid default
                enum=[1, 2, 3],  # Valid enum
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "default" in str(exc_info.value.message).lower()

    def test_valid_default_with_invalid_enum_raises_error(self) -> None:
        """Test that invalid enum raises error even with valid default."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelConfigSchemaProperty(
                type="integer",
                default=1,  # Valid default
                enum=[1, 2, "invalid"],  # Invalid enum
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "enum" in str(exc_info.value.message).lower()


# =============================================================================
# Unknown Type with Enum Tests
# =============================================================================


@pytest.mark.unit
class TestConfigSchemaPropertyEnumUnknownTypes:
    """Tests for unknown/custom type handling with enum values."""

    def test_unknown_type_allows_any_enum_values(self) -> None:
        """Test that unknown types don't trigger enum validation."""
        # 'array' type with various enum values
        prop1 = ModelConfigSchemaProperty(
            type="array",
            enum=["string_val", 42, True],  # Mixed types allowed for unknown type
            description="Test parameter",
        )
        assert prop1.enum == ["string_val", 42, True]

        # 'object' type with various enum values
        prop2 = ModelConfigSchemaProperty(
            type="object",
            enum=[1, 2, 3],
            description="Test parameter",
        )
        assert prop2.enum == [1, 2, 3]
