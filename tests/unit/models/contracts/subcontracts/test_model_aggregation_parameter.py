"""
Tests for ModelAggregationParameter.

Validates aggregation parameter configuration including
type safety, field constraints, and ModelSchemaValue integration.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_parameter_type import EnumParameterType
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.subcontracts.model_aggregation_parameter import (
    ModelAggregationParameter,
)


@pytest.mark.unit
class TestModelAggregationParameterValidation:
    """Test validation rules for aggregation parameters."""

    def test_valid_parameter_with_string_value(self) -> None:
        """Test that parameters with string values are valid."""
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="aggregation_field",
            parameter_value=ModelSchemaValue.create_string("total_count"),
        )
        assert param.parameter_name == "aggregation_field"
        assert param.parameter_value.is_string()
        assert param.parameter_value.get_string() == "total_count"

    def test_valid_parameter_with_number_value(self) -> None:
        """Test that parameters with numeric values are valid."""
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="threshold",
            parameter_value=ModelSchemaValue.create_number(100),
        )
        assert param.parameter_name == "threshold"
        assert param.parameter_value.is_number()

    def test_valid_parameter_with_boolean_value(self) -> None:
        """Test that parameters with boolean values are valid."""
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="include_nulls",
            parameter_value=ModelSchemaValue.create_boolean(True),
        )
        assert param.parameter_name == "include_nulls"
        assert param.parameter_value.is_boolean()
        assert param.parameter_value.get_boolean() is True

    def test_valid_parameter_with_array_value(self) -> None:
        """Test that parameters with array values are valid."""
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="field_names",
            parameter_value=ModelSchemaValue.create_array(
                ["field1", "field2", "field3"]
            ),
        )
        assert param.parameter_name == "field_names"
        assert param.parameter_value.is_array()
        assert len(param.parameter_value.get_array()) == 3

    def test_valid_parameter_with_object_value(self) -> None:
        """Test that parameters with object values are valid."""
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="config",
            parameter_value=ModelSchemaValue.create_object(
                {"key1": "value1", "key2": 42}
            ),
        )
        assert param.parameter_name == "config"
        assert param.parameter_value.is_object()
        assert len(param.parameter_value.get_object()) == 2

    def test_valid_parameter_with_required_flag(self) -> None:
        """Test that required parameters are valid."""
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="required_field",
            parameter_value=ModelSchemaValue.create_string("value"),
            is_required=True,
        )
        assert param.is_required is True

    def test_valid_parameter_with_default_value(self) -> None:
        """Test that parameters with default values are valid."""
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="optional_field",
            parameter_value=ModelSchemaValue.create_string("actual_value"),
            default_value=ModelSchemaValue.create_string("default_value"),
        )
        assert param.default_value is not None
        assert param.default_value.get_string() == "default_value"

    def test_valid_parameter_with_description(self) -> None:
        """Test that parameters with descriptions are valid."""
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="field",
            parameter_value=ModelSchemaValue.create_string("value"),
            description="This is a test parameter",
        )
        assert param.description == "This is a test parameter"


@pytest.mark.unit
class TestModelAggregationParameterCreation:
    """Test creation and field constraints."""

    def test_required_fields(self) -> None:
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            ModelAggregationParameter(version=DEFAULT_VERSION)  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            ModelAggregationParameter(
                version=DEFAULT_VERSION, parameter_name="field"
            )  # Missing parameter_value

        with pytest.raises(ValidationError):
            ModelAggregationParameter(  # Missing parameter_name
                parameter_value=ModelSchemaValue.create_string("value")
            )

    def test_default_values(self) -> None:
        """Test default field values."""
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="test_param",
            parameter_value=ModelSchemaValue.create_string("value"),
        )
        assert param.parameter_type == EnumParameterType.AUTO
        assert param.is_required is False
        assert param.default_value is None
        assert param.description is None

    def test_optional_fields(self) -> None:
        """Test optional field assignment."""
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="test_param",
            parameter_value=ModelSchemaValue.create_number(42),
            parameter_type=EnumParameterType.INTEGER,
            is_required=True,
            default_value=ModelSchemaValue.create_number(0),
            description="Test parameter description",
        )
        assert param.parameter_type == EnumParameterType.INTEGER
        assert param.is_required is True
        assert param.default_value is not None
        assert param.description == "Test parameter description"

    def test_string_field_constraints(self) -> None:
        """Test string field minimum length constraints."""
        with pytest.raises(ValidationError):
            ModelAggregationParameter(
                version=DEFAULT_VERSION,
                parameter_name="",  # Empty string not allowed
                parameter_value=ModelSchemaValue.create_string("value"),
            )

    def test_enum_values_for_parameter_type(self) -> None:
        """Test that parameter_type accepts all valid enum values."""
        for param_type in EnumParameterType:
            param = ModelAggregationParameter(
                version=DEFAULT_VERSION,
                parameter_name="test_param",
                parameter_value=ModelSchemaValue.create_string("value"),
                parameter_type=param_type,
            )
            assert param.parameter_type == param_type


@pytest.mark.unit
class TestModelAggregationParameterEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_parameter_name_with_special_characters(self) -> None:
        """Test that parameter names with special characters are valid."""
        special_names = [
            "param_with_underscore",
            "param-with-dash",
            "param.with.dot",
            "param123",
            "PARAM_UPPER",
            "param$special",
        ]
        for name in special_names:
            param = ModelAggregationParameter(
                version=DEFAULT_VERSION,
                parameter_name=name,
                parameter_value=ModelSchemaValue.create_string("value"),
            )
            assert param.parameter_name == name

    def test_parameter_name_with_unicode(self) -> None:
        """Test that parameter names with unicode characters are valid."""
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="参数名称",
            parameter_value=ModelSchemaValue.create_string("value"),
        )
        assert param.parameter_name == "参数名称"

    def test_parameter_with_null_default_value(self) -> None:
        """Test that null default values are valid."""
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="nullable_param",
            parameter_value=ModelSchemaValue.create_string("value"),
            default_value=ModelSchemaValue.create_null(),
        )
        assert param.default_value is not None
        assert param.default_value.is_null()

    def test_parameter_with_nested_array_value(self) -> None:
        """Test that parameters with nested array values are valid."""
        nested_array = [["a", "b"], ["c", "d"]]
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="nested_field",
            parameter_value=ModelSchemaValue.create_array(nested_array),
        )
        assert param.parameter_value.is_array()

    def test_parameter_with_nested_object_value(self) -> None:
        """Test that parameters with nested object values are valid."""
        nested_object = {"outer": {"inner": "value"}}
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="nested_config",
            parameter_value=ModelSchemaValue.create_object(nested_object),
        )
        assert param.parameter_value.is_object()

    def test_parameter_with_very_long_name(self) -> None:
        """Test that parameters with very long names are valid."""
        long_name = "a" * 1000
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name=long_name,
            parameter_value=ModelSchemaValue.create_string("value"),
        )
        assert param.parameter_name == long_name

    def test_parameter_with_very_long_description(self) -> None:
        """Test that parameters with very long descriptions are valid."""
        long_description = "This is a very long description. " * 100
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="field",
            parameter_value=ModelSchemaValue.create_string("value"),
            description=long_description,
        )
        assert param.description == long_description

    def test_required_parameter_with_no_default(self) -> None:
        """Test that required parameters without defaults are valid."""
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="required_field",
            parameter_value=ModelSchemaValue.create_string("value"),
            is_required=True,
            default_value=None,
        )
        assert param.is_required is True
        assert param.default_value is None

    def test_optional_parameter_with_default(self) -> None:
        """Test that optional parameters with defaults are valid."""
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="optional_field",
            parameter_value=ModelSchemaValue.create_string("value"),
            is_required=False,
            default_value=ModelSchemaValue.create_string("default"),
        )
        assert param.is_required is False
        assert param.default_value is not None

    def test_parameter_type_consistency_with_value_type(self) -> None:
        """Test parameters with matching parameter_type and value_type."""
        # String parameter with string value
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="string_param",
            parameter_value=ModelSchemaValue.create_string("text"),
            parameter_type=EnumParameterType.STRING,
        )
        assert param.parameter_type == EnumParameterType.STRING
        assert param.parameter_value.is_string()

        # Number parameter with number value
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="number_param",
            parameter_value=ModelSchemaValue.create_number(42),
            parameter_type=EnumParameterType.NUMBER,
        )
        assert param.parameter_type == EnumParameterType.NUMBER
        assert param.parameter_value.is_number()

        # Boolean parameter with boolean value
        param = ModelAggregationParameter(
            version=DEFAULT_VERSION,
            parameter_name="bool_param",
            parameter_value=ModelSchemaValue.create_boolean(True),
            parameter_type=EnumParameterType.BOOLEAN,
        )
        assert param.parameter_type == EnumParameterType.BOOLEAN
        assert param.parameter_value.is_boolean()
