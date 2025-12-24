"""
Test suite for ModelContractData - Discriminated union for contract data.

This test suite covers factory methods, type discrimination, and edge cases
for the ModelContractData discriminated union pattern.
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_contract_data_type import EnumContractDataType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.utils.model_contract_data import ModelContractData


@pytest.mark.unit
class TestModelContractDataInstantiation:
    """Test basic model instantiation."""

    def test_create_schema_values_type_directly(self):
        """Test creating SCHEMA_VALUES type directly."""
        schema_values = {"key": ModelSchemaValue.create_string("test")}
        contract_data = ModelContractData(
            data_type=EnumContractDataType.SCHEMA_VALUES,
            schema_values=schema_values,
        )
        assert contract_data.data_type == EnumContractDataType.SCHEMA_VALUES
        assert contract_data.schema_values == schema_values
        assert contract_data.raw_values is None

    def test_create_raw_values_type_directly(self):
        """Test creating RAW_VALUES type directly."""
        raw_values = {"key": ModelSchemaValue.create_number(42)}
        contract_data = ModelContractData(
            data_type=EnumContractDataType.RAW_VALUES,
            raw_values=raw_values,
        )
        assert contract_data.data_type == EnumContractDataType.RAW_VALUES
        assert contract_data.raw_values == raw_values
        assert contract_data.schema_values is None

    def test_create_none_type_directly(self):
        """Test creating NONE type directly."""
        contract_data = ModelContractData(data_type=EnumContractDataType.NONE)
        assert contract_data.data_type == EnumContractDataType.NONE
        assert contract_data.schema_values is None
        assert contract_data.raw_values is None


@pytest.mark.unit
class TestModelContractDataFromSchemaValues:
    """Test from_schema_values factory method."""

    def test_from_schema_values_single_string(self):
        """Test from_schema_values factory with single string value."""
        schema_values = {"name": ModelSchemaValue.create_string("test")}
        contract_data = ModelContractData.from_schema_values(schema_values)

        assert contract_data.data_type == EnumContractDataType.SCHEMA_VALUES
        assert contract_data.schema_values == schema_values
        assert contract_data.raw_values is None

    def test_from_schema_values_multiple_types(self):
        """Test from_schema_values factory with multiple value types."""
        schema_values = {
            "string_val": ModelSchemaValue.create_string("hello"),
            "number_val": ModelSchemaValue.create_number(42),
            "bool_val": ModelSchemaValue.create_boolean(True),
            "null_val": ModelSchemaValue.create_null(),
        }
        contract_data = ModelContractData.from_schema_values(schema_values)

        assert contract_data.data_type == EnumContractDataType.SCHEMA_VALUES
        assert contract_data.schema_values is not None
        assert len(contract_data.schema_values) == 4
        assert contract_data.schema_values["string_val"].is_string()
        assert contract_data.schema_values["number_val"].is_number()
        assert contract_data.schema_values["bool_val"].is_boolean()
        assert contract_data.schema_values["null_val"].is_null()

    def test_from_schema_values_empty_dict(self):
        """Test from_schema_values factory with empty dictionary."""
        schema_values: dict[str, ModelSchemaValue] = {}
        contract_data = ModelContractData.from_schema_values(schema_values)

        assert contract_data.data_type == EnumContractDataType.SCHEMA_VALUES
        assert contract_data.schema_values == {}
        assert len(contract_data.schema_values) == 0

    def test_from_schema_values_nested_array(self):
        """Test from_schema_values factory with array value."""
        schema_values = {
            "items": ModelSchemaValue.create_array([1, 2, 3]),
        }
        contract_data = ModelContractData.from_schema_values(schema_values)

        assert contract_data.data_type == EnumContractDataType.SCHEMA_VALUES
        assert contract_data.schema_values is not None
        assert contract_data.schema_values["items"].is_array()

    def test_from_schema_values_nested_object(self):
        """Test from_schema_values factory with nested object value."""
        schema_values = {
            "nested": ModelSchemaValue.create_object({"inner": "value"}),
        }
        contract_data = ModelContractData.from_schema_values(schema_values)

        assert contract_data.data_type == EnumContractDataType.SCHEMA_VALUES
        assert contract_data.schema_values is not None
        assert contract_data.schema_values["nested"].is_object()


@pytest.mark.unit
class TestModelContractDataFromRawValues:
    """Test from_raw_values factory method."""

    def test_from_raw_values_with_python_primitives(self):
        """Test from_raw_values factory with Python primitive values."""
        raw_values: dict[str, object] = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "boolean": True,
        }
        contract_data = ModelContractData.from_raw_values(raw_values)

        assert contract_data.data_type == EnumContractDataType.RAW_VALUES
        assert contract_data.raw_values is not None
        assert len(contract_data.raw_values) == 4
        # Values should be converted to ModelSchemaValue
        assert isinstance(contract_data.raw_values["string"], ModelSchemaValue)
        assert contract_data.raw_values["string"].is_string()
        assert contract_data.raw_values["number"].is_number()
        assert contract_data.raw_values["float"].is_number()
        assert contract_data.raw_values["boolean"].is_boolean()

    def test_from_raw_values_with_model_schema_values(self):
        """Test from_raw_values factory when values are already ModelSchemaValue."""
        raw_values: dict[str, ModelSchemaValue] = {
            "key1": ModelSchemaValue.create_string("value1"),
            "key2": ModelSchemaValue.create_number(100),
        }
        contract_data = ModelContractData.from_raw_values(raw_values)

        assert contract_data.data_type == EnumContractDataType.RAW_VALUES
        assert contract_data.raw_values is not None
        assert contract_data.raw_values == raw_values

    def test_from_raw_values_empty_dict(self):
        """Test from_raw_values factory with empty dictionary."""
        raw_values: dict[str, object] = {}
        contract_data = ModelContractData.from_raw_values(raw_values)

        assert contract_data.data_type == EnumContractDataType.RAW_VALUES
        # Empty dict goes through the cast branch
        assert contract_data.raw_values == {}

    def test_from_raw_values_with_null_python_value(self):
        """Test from_raw_values factory with Python None value."""
        raw_values: dict[str, object] = {"null_key": None}
        contract_data = ModelContractData.from_raw_values(raw_values)

        assert contract_data.data_type == EnumContractDataType.RAW_VALUES
        assert contract_data.raw_values is not None
        assert contract_data.raw_values["null_key"].is_null()

    def test_from_raw_values_with_list_value(self):
        """Test from_raw_values factory with list value."""
        raw_values: dict[str, object] = {
            "items": [1, 2, 3, "four"],
        }
        contract_data = ModelContractData.from_raw_values(raw_values)

        assert contract_data.data_type == EnumContractDataType.RAW_VALUES
        assert contract_data.raw_values is not None
        assert contract_data.raw_values["items"].is_array()

    def test_from_raw_values_with_nested_dict(self):
        """Test from_raw_values factory with nested dictionary."""
        raw_values: dict[str, object] = {
            "nested": {"inner_key": "inner_value"},
        }
        contract_data = ModelContractData.from_raw_values(raw_values)

        assert contract_data.data_type == EnumContractDataType.RAW_VALUES
        assert contract_data.raw_values is not None
        assert contract_data.raw_values["nested"].is_object()


@pytest.mark.unit
class TestModelContractDataFromNone:
    """Test from_none factory method."""

    def test_from_none_creates_empty_contract(self):
        """Test from_none factory creates empty contract data."""
        contract_data = ModelContractData.from_none()

        assert contract_data.data_type == EnumContractDataType.NONE
        assert contract_data.schema_values is None
        assert contract_data.raw_values is None

    def test_from_none_is_empty_returns_true(self):
        """Test from_none result reports as empty."""
        contract_data = ModelContractData.from_none()
        assert contract_data.is_empty() is True

    def test_from_none_to_schema_values_returns_none(self):
        """Test from_none conversion to schema values returns None."""
        contract_data = ModelContractData.from_none()
        assert contract_data.to_schema_values() is None


@pytest.mark.unit
class TestModelContractDataFromAny:
    """Test from_any factory method with automatic type detection."""

    def test_from_any_with_none_input(self):
        """Test from_any factory with None input."""
        contract_data = ModelContractData.from_any(None)

        assert contract_data.data_type == EnumContractDataType.NONE
        assert contract_data.is_empty() is True

    def test_from_any_with_schema_values(self):
        """Test from_any factory with ModelSchemaValue dictionary."""
        data: dict[str, ModelSchemaValue] = {
            "key": ModelSchemaValue.create_string("value"),
        }
        contract_data = ModelContractData.from_any(data)

        assert contract_data.data_type == EnumContractDataType.SCHEMA_VALUES
        assert contract_data.schema_values is not None
        assert contract_data.schema_values["key"].is_string()

    def test_from_any_with_raw_python_values(self):
        """Test from_any factory with raw Python values."""
        data: dict[str, object] = {
            "string": "hello",
            "number": 42,
        }
        contract_data = ModelContractData.from_any(data)

        assert contract_data.data_type == EnumContractDataType.RAW_VALUES
        assert contract_data.raw_values is not None
        assert contract_data.raw_values["string"].is_string()
        assert contract_data.raw_values["number"].is_number()

    def test_from_any_with_empty_dict_detects_as_raw(self):
        """Test from_any with empty dict treats as raw values."""
        data: dict[str, object] = {}
        contract_data = ModelContractData.from_any(data)

        # Empty dict - next(iter(data.values())) would fail, so it goes to raw_values
        assert contract_data.data_type == EnumContractDataType.RAW_VALUES

    def test_from_any_detects_first_value_type(self):
        """Test from_any correctly detects type from first value."""
        # First value is ModelSchemaValue
        schema_data: dict[str, ModelSchemaValue] = {
            "first": ModelSchemaValue.create_boolean(True),
            "second": ModelSchemaValue.create_number(99),
        }
        contract_data = ModelContractData.from_any(schema_data)
        assert contract_data.data_type == EnumContractDataType.SCHEMA_VALUES

    def test_from_any_with_mixed_nested_structures(self):
        """Test from_any with complex nested Python structures."""
        data: dict[str, object] = {
            "config": {
                "enabled": True,
                "count": 10,
            },
            "items": ["a", "b", "c"],
        }
        contract_data = ModelContractData.from_any(data)

        assert contract_data.data_type == EnumContractDataType.RAW_VALUES
        assert contract_data.raw_values is not None


@pytest.mark.unit
class TestModelContractDataToSchemaValues:
    """Test to_schema_values conversion method."""

    def test_to_schema_values_from_schema_values_type(self):
        """Test to_schema_values returns schema_values for SCHEMA_VALUES type."""
        schema_values = {"key": ModelSchemaValue.create_string("value")}
        contract_data = ModelContractData.from_schema_values(schema_values)

        result = contract_data.to_schema_values()
        assert result == schema_values

    def test_to_schema_values_from_raw_values_type(self):
        """Test to_schema_values returns raw_values for RAW_VALUES type."""
        raw_values: dict[str, object] = {"key": "value"}
        contract_data = ModelContractData.from_raw_values(raw_values)

        result = contract_data.to_schema_values()
        # raw_values are already converted to ModelSchemaValue
        assert result is not None
        assert result == contract_data.raw_values

    def test_to_schema_values_from_none_type(self):
        """Test to_schema_values returns None for NONE type."""
        contract_data = ModelContractData.from_none()

        result = contract_data.to_schema_values()
        assert result is None


@pytest.mark.unit
class TestModelContractDataIsEmpty:
    """Test is_empty method."""

    def test_is_empty_true_for_none_type(self):
        """Test is_empty returns True for NONE type."""
        contract_data = ModelContractData.from_none()
        assert contract_data.is_empty() is True

    def test_is_empty_false_for_schema_values_type(self):
        """Test is_empty returns False for SCHEMA_VALUES type."""
        schema_values = {"key": ModelSchemaValue.create_string("value")}
        contract_data = ModelContractData.from_schema_values(schema_values)
        assert contract_data.is_empty() is False

    def test_is_empty_false_for_empty_schema_values(self):
        """Test is_empty returns False for SCHEMA_VALUES type even when empty dict."""
        contract_data = ModelContractData.from_schema_values({})
        # Type is SCHEMA_VALUES, not NONE, so is_empty is False
        assert contract_data.is_empty() is False

    def test_is_empty_false_for_raw_values_type(self):
        """Test is_empty returns False for RAW_VALUES type."""
        raw_values: dict[str, object] = {"key": "value"}
        contract_data = ModelContractData.from_raw_values(raw_values)
        assert contract_data.is_empty() is False


@pytest.mark.unit
class TestModelContractDataTypeDiscrimination:
    """Test type discrimination behavior."""

    def test_data_type_enum_values(self):
        """Test all data_type enum values are handled correctly."""
        # SCHEMA_VALUES
        sv = ModelContractData.from_schema_values(
            {"k": ModelSchemaValue.create_string("v")}
        )
        assert sv.data_type == EnumContractDataType.SCHEMA_VALUES

        # RAW_VALUES
        rv = ModelContractData.from_raw_values({"k": "v"})
        assert rv.data_type == EnumContractDataType.RAW_VALUES

        # NONE
        nv = ModelContractData.from_none()
        assert nv.data_type == EnumContractDataType.NONE

    def test_only_one_storage_field_populated_for_schema_values(self):
        """Test only schema_values is populated for SCHEMA_VALUES type."""
        contract_data = ModelContractData.from_schema_values(
            {"key": ModelSchemaValue.create_string("value")}
        )
        assert contract_data.schema_values is not None
        assert contract_data.raw_values is None

    def test_only_one_storage_field_populated_for_raw_values(self):
        """Test only raw_values is populated for RAW_VALUES type."""
        contract_data = ModelContractData.from_raw_values({"key": "value"})
        assert contract_data.raw_values is not None
        assert contract_data.schema_values is None

    def test_no_storage_field_populated_for_none(self):
        """Test no storage fields populated for NONE type."""
        contract_data = ModelContractData.from_none()
        assert contract_data.schema_values is None
        assert contract_data.raw_values is None


@pytest.mark.unit
class TestModelContractDataEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_large_schema_values_dict(self):
        """Test with large schema values dictionary."""
        schema_values = {
            f"key_{i}": ModelSchemaValue.create_number(i) for i in range(100)
        }
        contract_data = ModelContractData.from_schema_values(schema_values)

        assert contract_data.data_type == EnumContractDataType.SCHEMA_VALUES
        assert contract_data.schema_values is not None
        assert len(contract_data.schema_values) == 100

    def test_large_raw_values_dict(self):
        """Test with large raw values dictionary."""
        raw_values: dict[str, object] = {f"key_{i}": i for i in range(100)}
        contract_data = ModelContractData.from_raw_values(raw_values)

        assert contract_data.data_type == EnumContractDataType.RAW_VALUES
        assert contract_data.raw_values is not None
        assert len(contract_data.raw_values) == 100

    def test_special_characters_in_keys(self):
        """Test handling of special characters in dictionary keys."""
        schema_values = {
            "key-with-dashes": ModelSchemaValue.create_string("v1"),
            "key.with.dots": ModelSchemaValue.create_string("v2"),
            "key_with_underscores": ModelSchemaValue.create_string("v3"),
            "key:with:colons": ModelSchemaValue.create_string("v4"),
            "key/with/slashes": ModelSchemaValue.create_string("v5"),
        }
        contract_data = ModelContractData.from_schema_values(schema_values)

        assert contract_data.schema_values is not None
        assert len(contract_data.schema_values) == 5

    def test_unicode_keys_and_values(self):
        """Test handling of unicode in keys and values."""
        schema_values = {
            "unicode_key": ModelSchemaValue.create_string("Hello, World!"),
            "emoji_value": ModelSchemaValue.create_string("Hello 😀"),
        }
        contract_data = ModelContractData.from_schema_values(schema_values)

        assert contract_data.schema_values is not None
        result = contract_data.to_schema_values()
        assert result is not None
        assert result["emoji_value"].get_string() == "Hello 😀"

    def test_round_trip_schema_values(self):
        """Test round-trip serialization with schema values."""
        original = ModelContractData.from_schema_values(
            {"key": ModelSchemaValue.create_string("test")}
        )
        dumped = original.model_dump()
        restored = ModelContractData(**dumped)

        assert restored.data_type == original.data_type
        assert restored.schema_values is not None
        assert original.schema_values is not None
        assert (
            restored.schema_values["key"].get_string()
            == original.schema_values["key"].get_string()
        )

    def test_round_trip_raw_values(self):
        """Test round-trip serialization with raw values."""
        original = ModelContractData.from_raw_values({"key": "value"})
        dumped = original.model_dump()
        restored = ModelContractData(**dumped)

        assert restored.data_type == EnumContractDataType.RAW_VALUES
        assert restored.raw_values is not None

    def test_round_trip_none(self):
        """Test round-trip serialization with none type."""
        original = ModelContractData.from_none()
        dumped = original.model_dump()
        restored = ModelContractData(**dumped)

        assert restored.data_type == EnumContractDataType.NONE
        assert restored.is_empty() is True

    def test_model_dump_preserves_type(self):
        """Test Pydantic model_dump preserves data_type."""
        contract_data = ModelContractData.from_schema_values(
            {"key": ModelSchemaValue.create_boolean(True)}
        )
        dumped = contract_data.model_dump()

        assert dumped["data_type"] == EnumContractDataType.SCHEMA_VALUES
        assert dumped["schema_values"] is not None
        assert dumped["raw_values"] is None

    def test_from_attributes_config(self):
        """Test from_attributes=True config enables attribute-based instantiation."""
        # This is important for pytest-xdist compatibility
        schema_values = {"key": ModelSchemaValue.create_string("value")}
        contract_data = ModelContractData.from_schema_values(schema_values)

        # Verify config is set
        assert contract_data.model_config.get("from_attributes") is True

    def test_deeply_nested_raw_values(self):
        """Test from_raw_values with deeply nested structures."""
        raw_values: dict[str, object] = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep",
                    },
                },
            },
        }
        contract_data = ModelContractData.from_raw_values(raw_values)

        assert contract_data.data_type == EnumContractDataType.RAW_VALUES
        assert contract_data.raw_values is not None
        assert contract_data.raw_values["level1"].is_object()


@pytest.mark.unit
class TestModelContractDataConversionBranches:
    """Test specific branches in conversion logic."""

    def test_from_raw_values_conversion_branch_single_key(self):
        """Test conversion branch in from_raw_values with single primitive key."""
        # This hits: values and len(values) > 0 and not isinstance(...)
        raw_values: dict[str, object] = {"single": "value"}
        contract_data = ModelContractData.from_raw_values(raw_values)

        assert contract_data.raw_values is not None
        assert contract_data.raw_values["single"].is_string()
        assert contract_data.raw_values["single"].get_string() == "value"

    def test_from_raw_values_no_conversion_branch(self):
        """Test no-conversion branch in from_raw_values with ModelSchemaValue."""
        # This hits the else branch: values already contain ModelSchemaValue
        raw_values: dict[str, ModelSchemaValue] = {
            "already_converted": ModelSchemaValue.create_number(42),
        }
        contract_data = ModelContractData.from_raw_values(raw_values)

        assert contract_data.raw_values is not None
        # Values should pass through unchanged
        assert (
            contract_data.raw_values["already_converted"]
            == raw_values["already_converted"]
        )

    def test_from_any_schema_detection_branch(self):
        """Test schema detection branch in from_any."""
        # This hits: data and isinstance(next(iter(data.values())), ModelSchemaValue)
        data: dict[str, ModelSchemaValue] = {
            "detected": ModelSchemaValue.create_boolean(False),
        }
        contract_data = ModelContractData.from_any(data)

        assert contract_data.data_type == EnumContractDataType.SCHEMA_VALUES

    def test_from_any_raw_fallback_branch(self):
        """Test raw fallback branch in from_any."""
        # This hits: else branch treating as raw values
        data: dict[str, object] = {"raw": 123}
        contract_data = ModelContractData.from_any(data)

        assert contract_data.data_type == EnumContractDataType.RAW_VALUES
