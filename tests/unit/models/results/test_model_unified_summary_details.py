# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Comprehensive tests for ModelUnifiedSummaryDetails.

Tests cover:
- Basic instantiation with optional fields
- Key-value pair handling
- ModelSchemaValue type usage (strongly typed)
- arbitrary_types_allowed config
- Type safety verification
"""

import pytest

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.results.model_unified_summary_details import (
    ModelUnifiedSummaryDetails,
)


@pytest.mark.unit
class TestModelUnifiedSummaryDetailsBasicInstantiation:
    """Test basic instantiation."""

    def test_empty_instantiation(self):
        """Test creating details with no fields."""
        details = ModelUnifiedSummaryDetails()

        assert details.key is None
        assert details.value is None

    def test_instantiation_with_key_only(self):
        """Test creating details with key only."""
        details = ModelUnifiedSummaryDetails(key="coverage")

        assert details.key == "coverage"
        assert details.value is None

    def test_instantiation_with_key_and_value(self):
        """Test creating details with key and value - automatically converts to ModelSchemaValue."""
        details = ModelUnifiedSummaryDetails(
            key="coverage", value=ModelSchemaValue.from_value("85.5")
        )

        assert details.key == "coverage"
        assert isinstance(details.value, ModelSchemaValue)
        assert details.value.string_value == "85.5"


@pytest.mark.unit
class TestModelUnifiedSummaryDetailsKeyField:
    """Test key field handling."""

    def test_key_field_with_string(self):
        """Test key field with string value."""
        details = ModelUnifiedSummaryDetails(key="metric_name")
        assert details.key == "metric_name"

    def test_key_field_optional(self):
        """Test that key field is optional."""
        details = ModelUnifiedSummaryDetails()
        assert details.key is None

    def test_key_field_with_various_names(self):
        """Test key field with different naming conventions."""
        keys = [
            "simple",
            "snake_case",
            "camelCase",
            "with.dots",
            "with-dashes",
            "UPPERCASE",
        ]

        for key in keys:
            details = ModelUnifiedSummaryDetails(key=key)
            assert details.key == key


@pytest.mark.unit
class TestModelUnifiedSummaryDetailsValueField:
    """Test value field with ModelSchemaValue type (strongly typed)."""

    def test_value_field_with_string(self):
        """Test value field with string - converts to ModelSchemaValue."""
        details = ModelUnifiedSummaryDetails(
            key="key", value=ModelSchemaValue.from_value("string_value")
        )
        assert isinstance(details.value, ModelSchemaValue)
        assert details.value.string_value == "string_value"

    def test_value_field_with_integer(self):
        """Test value field with integer - converts to ModelSchemaValue."""
        details = ModelUnifiedSummaryDetails(
            key="key", value=ModelSchemaValue.from_value(42)
        )
        assert isinstance(details.value, ModelSchemaValue)
        assert details.value.number_value == 42

    def test_value_field_with_float(self):
        """Test value field with float - converts to ModelSchemaValue."""
        details = ModelUnifiedSummaryDetails(
            key="key", value=ModelSchemaValue.from_value(85.5)
        )
        assert isinstance(details.value, ModelSchemaValue)
        assert details.value.number_value == 85.5

    def test_value_field_with_boolean(self):
        """Test value field with boolean - converts to ModelSchemaValue."""
        details = ModelUnifiedSummaryDetails(
            key="key", value=ModelSchemaValue.from_value(True)
        )
        assert isinstance(details.value, ModelSchemaValue)
        assert details.value.boolean_value is True

        details = ModelUnifiedSummaryDetails(
            key="key", value=ModelSchemaValue.from_value(False)
        )
        assert isinstance(details.value, ModelSchemaValue)
        assert details.value.boolean_value is False

    def test_value_field_with_none(self):
        """Test value field with None."""
        details = ModelUnifiedSummaryDetails(key="key", value=None)
        assert details.value is None

    def test_value_field_with_list_of_strings(self):
        """Test value field with list - converts to ModelSchemaValue."""
        value_list = ["item1", "item2", "item3"]
        details = ModelUnifiedSummaryDetails(
            key="key", value=ModelSchemaValue.from_value(value_list)
        )
        assert isinstance(details.value, ModelSchemaValue)
        assert details.value.value_type == "array"
        assert len(details.value.array_value) == 3

    def test_value_field_with_dict_of_strings(self):
        """Test value field with dict - converts to ModelSchemaValue."""
        value_dict = {"nested_key": "nested_value"}
        details = ModelUnifiedSummaryDetails(
            key="key", value=ModelSchemaValue.from_value(value_dict)
        )
        assert isinstance(details.value, ModelSchemaValue)
        assert details.value.value_type == "object"
        assert "nested_key" in details.value.object_value

    def test_value_field_defaults_to_none(self):
        """Test that value field defaults to None."""
        details = ModelUnifiedSummaryDetails(key="key")
        assert details.value is None


@pytest.mark.unit
class TestModelUnifiedSummaryDetailsModelConfig:
    """Test Pydantic model_config settings."""

    def test_arbitrary_types_allowed_config(self):
        """Test that arbitrary_types_allowed is configured correctly."""
        assert (
            ModelUnifiedSummaryDetails.model_config["arbitrary_types_allowed"] is True
        )


@pytest.mark.unit
class TestModelUnifiedSummaryDetailsFieldValidation:
    """Test field validation."""

    def test_key_must_be_string_or_none(self):
        """Test that key field accepts string or None."""
        # Valid string
        details = ModelUnifiedSummaryDetails(key="valid_string")
        assert isinstance(details.key, str)

        # Valid None
        details = ModelUnifiedSummaryDetails(key=None)
        assert details.key is None

    def test_value_accepts_schema_value_types(self):
        """Test that value field accepts various types and converts to ModelSchemaValue."""
        # String
        details = ModelUnifiedSummaryDetails(
            value=ModelSchemaValue.from_value("string")
        )
        assert isinstance(details.value, ModelSchemaValue)

        # Integer
        details = ModelUnifiedSummaryDetails(value=ModelSchemaValue.from_value(42))
        assert isinstance(details.value, ModelSchemaValue)

        # Float
        details = ModelUnifiedSummaryDetails(value=ModelSchemaValue.from_value(3.14))
        assert isinstance(details.value, ModelSchemaValue)

        # Boolean
        details = ModelUnifiedSummaryDetails(value=ModelSchemaValue.from_value(True))
        assert isinstance(details.value, ModelSchemaValue)

        # List
        details = ModelUnifiedSummaryDetails(
            value=ModelSchemaValue.from_value(["a", "b"])
        )
        assert isinstance(details.value, ModelSchemaValue)

        # Dict
        details = ModelUnifiedSummaryDetails(
            value=ModelSchemaValue.from_value({"key": "value"})
        )
        assert isinstance(details.value, ModelSchemaValue)

        # None
        details = ModelUnifiedSummaryDetails(value=None)
        assert details.value is None


@pytest.mark.unit
class TestModelUnifiedSummaryDetailsSerialization:
    """Test model serialization and deserialization."""

    def test_model_dump_basic(self):
        """Test model_dump() produces correct dictionary with ModelSchemaValue."""
        details = ModelUnifiedSummaryDetails(
            key="metric", value=ModelSchemaValue.from_value("85.5")
        )

        dumped = details.model_dump()

        assert dumped["key"] == "metric"
        assert isinstance(dumped["value"], dict)  # ModelSchemaValue serializes to dict
        assert dumped["value"]["string_value"] == "85.5"

    def test_model_dump_with_complex_value(self):
        """Test model_dump() with complex value types."""
        value_dict = {"nested": "data", "count": "10"}
        details = ModelUnifiedSummaryDetails(
            key="complex", value=ModelSchemaValue.from_value(value_dict)
        )

        dumped = details.model_dump()

        assert dumped["key"] == "complex"
        assert isinstance(dumped["value"], dict)  # ModelSchemaValue serializes to dict
        assert dumped["value"]["value_type"] == "object"
        assert "nested" in dumped["value"]["object_value"]

    def test_model_dump_exclude_none(self):
        """Test model_dump(exclude_none=True) removes None fields."""
        details = ModelUnifiedSummaryDetails(key="key")

        dumped = details.model_dump(exclude_none=True)

        assert "key" in dumped
        assert "value" not in dumped

    def test_model_dump_json_roundtrip(self):
        """Test JSON serialization roundtrip."""
        original = ModelUnifiedSummaryDetails(
            key="metric", value=ModelSchemaValue.from_value("85.5")
        )

        json_str = original.model_dump_json()
        restored = ModelUnifiedSummaryDetails.model_validate_json(json_str)

        assert restored.key == original.key
        assert isinstance(restored.value, ModelSchemaValue)
        # String value should remain string type after roundtrip
        assert restored.value.value_type == "string"
        assert restored.value.string_value == "85.5"


@pytest.mark.unit
class TestModelUnifiedSummaryDetailsComplexScenarios:
    """Test complex usage scenarios."""

    def test_details_with_coverage_metric(self):
        """Test details holding coverage metric."""
        details = ModelUnifiedSummaryDetails(
            key="code_coverage", value=ModelSchemaValue.from_value("85.5")
        )

        assert details.key == "code_coverage"
        assert isinstance(details.value, ModelSchemaValue)
        assert details.value.string_value == "85.5"

    def test_details_with_duration_metric(self):
        """Test details holding duration metric."""
        details = ModelUnifiedSummaryDetails(
            key="total_duration_seconds", value=ModelSchemaValue.from_value("120")
        )

        assert details.key == "total_duration_seconds"
        assert isinstance(details.value, ModelSchemaValue)
        assert details.value.string_value == "120"

    def test_details_with_boolean_flag(self):
        """Test details with boolean flag."""
        details = ModelUnifiedSummaryDetails(
            key="auto_fix_applied", value=ModelSchemaValue.from_value(True)
        )

        assert details.key == "auto_fix_applied"
        assert isinstance(details.value, ModelSchemaValue)
        assert details.value.boolean_value is True

    def test_details_with_numeric_value(self):
        """Test details with numeric value."""
        details = ModelUnifiedSummaryDetails(
            key="test_count", value=ModelSchemaValue.from_value(250)
        )

        assert details.key == "test_count"
        assert isinstance(details.value, ModelSchemaValue)
        assert details.value.number_value == 250

    def test_multiple_details_in_list(self):
        """Test creating multiple details instances."""
        details_list = [
            ModelUnifiedSummaryDetails(
                key="coverage", value=ModelSchemaValue.from_value("85.5")
            ),
            ModelUnifiedSummaryDetails(
                key="duration", value=ModelSchemaValue.from_value("120")
            ),
            ModelUnifiedSummaryDetails(
                key="test_count", value=ModelSchemaValue.from_value(250)
            ),
        ]

        assert len(details_list) == 3
        assert details_list[0].key == "coverage"
        assert details_list[1].key == "duration"
        assert isinstance(details_list[2].value, ModelSchemaValue)
        assert details_list[2].value.number_value == 250


@pytest.mark.unit
class TestModelUnifiedSummaryDetailsTypeSafety:
    """Test type safety - comprehensive testing required."""

    def test_value_uses_model_schema_value_not_any(self):
        """Test that value field uses ModelSchemaValue type, not Any."""
        from typing import get_type_hints

        hints = get_type_hints(ModelUnifiedSummaryDetails)
        value_type = hints.get("value")

        assert value_type is not None
        type_str = str(value_type)
        # Should use ModelSchemaValue, not Any or loose unions
        assert "ModelSchemaValue" in type_str

    def test_no_any_types_in_annotations(self):
        """Test that model fields don't use Any type."""
        from typing import get_type_hints

        hints = get_type_hints(ModelUnifiedSummaryDetails)

        # Check that no field uses Any type directly
        for field_name, field_type in hints.items():
            type_str = str(field_type)
            # Allow typing.Any only in union with other types
            assert "typing.Any" not in type_str or "None" in type_str, (
                f"Field {field_name} uses Any type: {type_str}"
            )


@pytest.mark.unit
class TestModelUnifiedSummaryDetailsEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_string_key(self):
        """Test details with empty string key."""
        details = ModelUnifiedSummaryDetails(
            key="", value=ModelSchemaValue.from_value("value")
        )
        assert details.key == ""

    def test_empty_string_value(self):
        """Test details with empty string value."""
        details = ModelUnifiedSummaryDetails(
            key="key", value=ModelSchemaValue.from_value("")
        )
        assert isinstance(details.value, ModelSchemaValue)
        assert details.value.string_value == ""

    def test_zero_integer_value(self):
        """Test details with zero integer value."""
        details = ModelUnifiedSummaryDetails(
            key="count", value=ModelSchemaValue.from_value(0)
        )
        assert isinstance(details.value, ModelSchemaValue)
        assert details.value.number_value == 0

    def test_empty_list_value(self):
        """Test details with empty list value."""
        details = ModelUnifiedSummaryDetails(
            key="items", value=ModelSchemaValue.from_value([])
        )
        assert isinstance(details.value, ModelSchemaValue)
        assert details.value.array_value == []

    def test_empty_dict_value(self):
        """Test details with empty dict value."""
        details = ModelUnifiedSummaryDetails(
            key="data", value=ModelSchemaValue.from_value({})
        )
        assert isinstance(details.value, ModelSchemaValue)
        assert details.value.object_value == {}
