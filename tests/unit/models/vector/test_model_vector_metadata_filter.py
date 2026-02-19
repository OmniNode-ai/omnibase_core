# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelVectorMetadataFilter."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.vector import (
    EnumVectorFilterOperator,
    ModelVectorMetadataFilter,
)


@pytest.mark.unit
class TestModelVectorMetadataFilterInstantiation:
    """Tests for ModelVectorMetadataFilter instantiation."""

    def test_create_eq_filter(self):
        """Test creating equality filter."""
        filter_model = ModelVectorMetadataFilter(
            field="category",
            operator=EnumVectorFilterOperator.EQ,
            value=ModelSchemaValue.from_value("science"),
        )
        assert filter_model.field == "category"
        assert filter_model.operator == EnumVectorFilterOperator.EQ
        assert filter_model.value.to_value() == "science"

    def test_create_comparison_filter(self):
        """Test creating comparison filter."""
        filter_model = ModelVectorMetadataFilter(
            field="year",
            operator=EnumVectorFilterOperator.GTE,
            value=ModelSchemaValue.from_value(2020),
        )
        assert filter_model.field == "year"
        assert filter_model.operator == EnumVectorFilterOperator.GTE
        assert filter_model.value.to_value() == 2020

    def test_create_in_filter(self):
        """Test creating IN filter."""
        filter_model = ModelVectorMetadataFilter(
            field="status",
            operator=EnumVectorFilterOperator.IN,
            value=ModelSchemaValue.from_value(["published", "reviewed"]),
        )
        assert filter_model.operator == EnumVectorFilterOperator.IN
        assert filter_model.value.to_value() == ["published", "reviewed"]

    def test_create_exists_filter(self):
        """Test creating EXISTS filter."""
        filter_model = ModelVectorMetadataFilter(
            field="optional_field",
            operator=EnumVectorFilterOperator.EXISTS,
            value=ModelSchemaValue.from_value(True),
        )
        assert filter_model.operator == EnumVectorFilterOperator.EXISTS


@pytest.mark.unit
class TestModelVectorMetadataFilterValidation:
    """Tests for ModelVectorMetadataFilter validation."""

    def test_empty_field_raises(self):
        """Test that empty field raises validation error."""
        with pytest.raises(ValidationError):
            ModelVectorMetadataFilter(
                field="",
                operator=EnumVectorFilterOperator.EQ,
                value=ModelSchemaValue.from_value("test"),
            )

    def test_missing_field_raises(self):
        """Test that missing field raises validation error."""
        with pytest.raises(ValidationError):
            ModelVectorMetadataFilter(
                operator=EnumVectorFilterOperator.EQ,
                value=ModelSchemaValue.from_value("test"),
            )  # type: ignore[call-arg]

    def test_missing_operator_raises(self):
        """Test that missing operator raises validation error."""
        with pytest.raises(ValidationError):
            ModelVectorMetadataFilter(
                field="category",
                value=ModelSchemaValue.from_value("test"),
            )  # type: ignore[call-arg]

    def test_missing_value_raises(self):
        """Test that missing value raises validation error."""
        with pytest.raises(ValidationError):
            ModelVectorMetadataFilter(
                field="category",
                operator=EnumVectorFilterOperator.EQ,
            )  # type: ignore[call-arg]

    def test_extra_fields_forbidden(self):
        """Test that extra fields raise validation error."""
        with pytest.raises(ValidationError):
            ModelVectorMetadataFilter(
                field="category",
                operator=EnumVectorFilterOperator.EQ,
                value=ModelSchemaValue.from_value("test"),
                extra="not_allowed",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelVectorMetadataFilterImmutability:
    """Tests for ModelVectorMetadataFilter immutability."""

    def test_frozen_model(self):
        """Test that the model is frozen (immutable)."""
        filter_model = ModelVectorMetadataFilter(
            field="category",
            operator=EnumVectorFilterOperator.EQ,
            value=ModelSchemaValue.from_value("test"),
        )
        with pytest.raises(ValidationError):
            filter_model.field = "new_field"  # type: ignore[misc]


@pytest.mark.unit
class TestModelVectorMetadataFilterSerialization:
    """Tests for ModelVectorMetadataFilter serialization."""

    def test_model_dump(self):
        """Test model_dump method."""
        filter_model = ModelVectorMetadataFilter(
            field="category",
            operator=EnumVectorFilterOperator.EQ,
            value=ModelSchemaValue.from_value("science"),
        )
        data = filter_model.model_dump()
        assert isinstance(data, dict)
        assert data["field"] == "category"
        assert data["operator"] == "eq"

    def test_model_validate(self):
        """Test deserializing from dictionary via model_validate."""
        data = {
            "field": "year",
            "operator": "gte",
            "value": {
                "value_type": "number",
                "string_value": None,
                "boolean_value": None,
                "null_value": None,
                "array_value": None,
                "object_value": None,
                "number_value": {
                    "value": 2020.0,
                    "value_type": "integer",
                    "is_validated": True,
                    "source": None,
                },
            },
        }
        filter_model = ModelVectorMetadataFilter.model_validate(data)
        assert filter_model.field == "year"
        assert filter_model.operator == EnumVectorFilterOperator.GTE
        assert filter_model.value.to_value() == 2020


@pytest.mark.unit
class TestModelVectorMetadataFilterEdgeCases:
    """Tests for ModelVectorMetadataFilter edge cases."""

    def test_unicode_field_name(self):
        """Test filter with unicode field name."""
        filter_model = ModelVectorMetadataFilter(
            field="field_\u4e2d\u6587_name",
            operator=EnumVectorFilterOperator.EQ,
            value=ModelSchemaValue.from_value("test"),
        )
        assert filter_model.field == "field_\u4e2d\u6587_name"

    def test_numeric_value(self):
        """Test filter with numeric value."""
        filter_model = ModelVectorMetadataFilter(
            field="count",
            operator=EnumVectorFilterOperator.GT,
            value=ModelSchemaValue.from_value(100),
        )
        assert filter_model.value.to_value() == 100

    def test_boolean_value(self):
        """Test filter with boolean value."""
        filter_model = ModelVectorMetadataFilter(
            field="is_active",
            operator=EnumVectorFilterOperator.EQ,
            value=ModelSchemaValue.from_value(True),
        )
        assert filter_model.value.to_value() is True
