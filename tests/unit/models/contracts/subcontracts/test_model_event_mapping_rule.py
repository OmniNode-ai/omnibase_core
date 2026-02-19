# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelEventMappingRule.

Comprehensive test coverage for event mapping rule model including:
- Field validation and constraints
- Enum type validation
- Priority bounds validation
- Conditional logic fields
- Default values
- ConfigDict behavior
- Edge cases and error scenarios
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)

from omnibase_core.enums.enum_mapping_type import EnumMappingType
from omnibase_core.models.contracts.subcontracts.model_event_mapping_rule import (
    ModelEventMappingRule,
)


@pytest.mark.unit
class TestModelEventMappingRuleBasics:
    """Test basic model instantiation and defaults."""

    def test_minimal_instantiation(self):
        """Test model can be instantiated with minimal required fields."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="user_id",
            target_field="userId",
        )

        assert rule.source_field == "user_id"
        assert rule.target_field == "userId"
        assert rule.mapping_type == EnumMappingType.DIRECT
        assert rule.transformation_expression is None
        assert rule.default_value is None
        assert rule.is_required is False
        assert rule.apply_condition is None
        assert rule.priority == 100

    def test_full_instantiation(self):
        """Test model with all fields specified."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="timestamp",
            target_field="created_at",
            mapping_type=EnumMappingType.TRANSFORM,
            transformation_expression="datetime.fromisoformat({timestamp})",
            default_value="2024-01-01T00:00:00Z",
            is_required=True,
            apply_condition="timestamp is not None",
            priority=500,
        )

        assert rule.source_field == "timestamp"
        assert rule.target_field == "created_at"
        assert rule.mapping_type == EnumMappingType.TRANSFORM
        assert rule.transformation_expression == "datetime.fromisoformat({timestamp})"
        assert rule.default_value == "2024-01-01T00:00:00Z"
        assert rule.is_required is True
        assert rule.apply_condition == "timestamp is not None"
        assert rule.priority == 500

    def test_default_mapping_type(self):
        """Test mapping_type defaults to DIRECT."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="name",
            target_field="full_name",
        )

        assert rule.mapping_type == EnumMappingType.DIRECT

    def test_default_priority(self):
        """Test priority defaults to 100."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="id",
            target_field="identifier",
        )

        assert rule.priority == 100

    def test_default_is_required(self):
        """Test is_required defaults to False."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="optional_field",
            target_field="target",
        )

        assert rule.is_required is False


@pytest.mark.unit
class TestModelEventMappingRuleValidation:
    """Test field validation and constraints."""

    def test_source_field_required(self):
        """Test source_field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventMappingRule(version=DEFAULT_VERSION, target_field="target")

        assert "source_field" in str(exc_info.value)

    def test_source_field_min_length(self):
        """Test source_field has minimum length constraint."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventMappingRule(
                version=DEFAULT_VERSION,
                source_field="",
                target_field="target",
            )

        assert "source_field" in str(exc_info.value)

    def test_source_field_whitespace_accepted(self):
        """Test source_field accepts whitespace (no strip validation)."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="   ",
            target_field="target",
        )
        # Pydantic doesn't strip by default, so whitespace is accepted
        assert rule.source_field == "   "

    def test_target_field_required(self):
        """Test target_field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventMappingRule(version=DEFAULT_VERSION, source_field="source")

        assert "target_field" in str(exc_info.value)

    def test_target_field_min_length(self):
        """Test target_field has minimum length constraint."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventMappingRule(
                version=DEFAULT_VERSION,
                source_field="source",
                target_field="",
            )

        assert "target_field" in str(exc_info.value)

    def test_target_field_whitespace_accepted(self):
        """Test target_field accepts whitespace (no strip validation)."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="source",
            target_field="   ",
        )
        # Pydantic doesn't strip by default, so whitespace is accepted
        assert rule.target_field == "   "

    def test_mapping_type_enum_values(self):
        """Test mapping_type accepts all enum values."""
        for mapping_type in EnumMappingType:
            rule = ModelEventMappingRule(
                version=DEFAULT_VERSION,
                source_field="source",
                target_field="target",
                mapping_type=mapping_type,
            )
            assert rule.mapping_type == mapping_type

    def test_mapping_type_invalid_value(self):
        """Test mapping_type rejects invalid values."""
        with pytest.raises(ValidationError):
            ModelEventMappingRule(
                version=DEFAULT_VERSION,
                source_field="source",
                target_field="target",
                mapping_type="invalid_type",  # type: ignore[arg-type]
            )

    def test_priority_bounds_minimum(self):
        """Test priority minimum bound (0)."""
        # Valid minimum
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="source",
            target_field="target",
            priority=0,
        )
        assert rule.priority == 0

        # Invalid negative
        with pytest.raises(ValidationError) as exc_info:
            ModelEventMappingRule(
                version=DEFAULT_VERSION,
                source_field="source",
                target_field="target",
                priority=-1,
            )

        assert "priority" in str(exc_info.value)

    def test_priority_bounds_maximum(self):
        """Test priority maximum bound (1000)."""
        # Valid maximum
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="source",
            target_field="target",
            priority=1000,
        )
        assert rule.priority == 1000

        # Invalid exceeds maximum
        with pytest.raises(ValidationError) as exc_info:
            ModelEventMappingRule(
                version=DEFAULT_VERSION,
                source_field="source",
                target_field="target",
                priority=1001,
            )

        assert "priority" in str(exc_info.value)

    def test_priority_mid_range(self):
        """Test priority accepts mid-range values."""
        for priority in [1, 50, 100, 250, 500, 750, 999]:
            rule = ModelEventMappingRule(
                version=DEFAULT_VERSION,
                source_field="source",
                target_field="target",
                priority=priority,
            )
            assert rule.priority == priority

    def test_optional_fields_none_accepted(self):
        """Test optional fields accept None values."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="source",
            target_field="target",
            transformation_expression=None,
            default_value=None,
            apply_condition=None,
        )

        assert rule.transformation_expression is None
        assert rule.default_value is None
        assert rule.apply_condition is None


@pytest.mark.unit
class TestModelEventMappingRuleEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_direct_mapping_no_transformation(self):
        """Test DIRECT mapping type without transformation."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="email",
            target_field="email_address",
            mapping_type=EnumMappingType.DIRECT,
        )

        assert rule.mapping_type == EnumMappingType.DIRECT
        assert rule.transformation_expression is None

    def test_transform_mapping_with_expression(self):
        """Test TRANSFORM mapping with transformation expression."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="price",
            target_field="price_usd",
            mapping_type=EnumMappingType.TRANSFORM,
            transformation_expression="{price} * 1.1",
        )

        assert rule.mapping_type == EnumMappingType.TRANSFORM
        assert rule.transformation_expression == "{price} * 1.1"

    def test_conditional_mapping_with_condition(self):
        """Test CONDITIONAL mapping with apply condition."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="discount",
            target_field="final_discount",
            mapping_type=EnumMappingType.CONDITIONAL,
            apply_condition="discount > 0",
            default_value="0",
        )

        assert rule.mapping_type == EnumMappingType.CONDITIONAL
        assert rule.apply_condition == "discount > 0"
        assert rule.default_value == "0"

    def test_composite_mapping(self):
        """Test COMPOSITE mapping type."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="first_name,last_name",
            target_field="full_name",
            mapping_type=EnumMappingType.COMPOSITE,
            transformation_expression="{first_name} {last_name}",
        )

        assert rule.mapping_type == EnumMappingType.COMPOSITE
        assert "," in rule.source_field

    def test_required_field_with_default(self):
        """Test required field can have default value."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="status",
            target_field="order_status",
            is_required=True,
            default_value="pending",
        )

        assert rule.is_required is True
        assert rule.default_value == "pending"

    def test_high_priority_mapping(self):
        """Test high priority mapping rule."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="id",
            target_field="primary_id",
            priority=1000,
        )

        assert rule.priority == 1000

    def test_low_priority_mapping(self):
        """Test low priority mapping rule."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="metadata",
            target_field="extra_data",
            priority=0,
        )

        assert rule.priority == 0

    def test_long_field_names(self):
        """Test with very long field names."""
        long_source = "very_long_nested_source_field_name_with_many_parts"
        long_target = "extremely_long_target_field_name_after_transformation"

        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field=long_source,
            target_field=long_target,
        )

        assert rule.source_field == long_source
        assert rule.target_field == long_target

    def test_dotted_field_notation(self):
        """Test field names with dot notation."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="user.profile.email",
            target_field="contact.email",
        )

        assert rule.source_field == "user.profile.email"
        assert rule.target_field == "contact.email"

    def test_array_index_notation(self):
        """Test field names with array index notation."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="items[0].price",
            target_field="first_item_price",
        )

        assert rule.source_field == "items[0].price"
        assert rule.target_field == "first_item_price"

    def test_complex_transformation_expression(self):
        """Test complex transformation expression."""
        expression = """
        if {age} >= 18:
            return 'adult'
        else:
            return 'minor'
        """.strip()

        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="age",
            target_field="age_category",
            mapping_type=EnumMappingType.TRANSFORM,
            transformation_expression=expression,
        )

        assert rule.transformation_expression == expression

    def test_json_path_transformation(self):
        """Test transformation expression with JSON path."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="response",
            target_field="status_code",
            mapping_type=EnumMappingType.TRANSFORM,
            transformation_expression="$.response.statusCode",
        )

        assert rule.transformation_expression == "$.response.statusCode"

    def test_complex_apply_condition(self):
        """Test complex apply condition."""
        condition = (
            "status == 'active' and subscription_type in ['premium', 'enterprise']"
        )

        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="discount_rate",
            target_field="applied_discount",
            mapping_type=EnumMappingType.CONDITIONAL,
            apply_condition=condition,
        )

        assert rule.apply_condition == condition

    def test_empty_default_value(self):
        """Test empty string as default value."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="optional",
            target_field="target",
            default_value="",
        )

        assert rule.default_value == ""

    def test_json_default_value(self):
        """Test JSON string as default value."""
        json_default = '{"status": "unknown", "code": 0}'

        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="response",
            target_field="parsed_response",
            default_value=json_default,
        )

        assert rule.default_value == json_default


@pytest.mark.unit
class TestModelEventMappingRuleConfigDict:
    """Test ConfigDict behavior."""

    def test_extra_fields_ignored(self):
        """Test extra fields are ignored per ConfigDict."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="source",
            target_field="target",
            unknown_field="should_be_ignored",  # type: ignore[call-arg]
        )

        assert rule.source_field == "source"
        assert not hasattr(rule, "unknown_field")

    def test_validate_assignment(self):
        """Test assignment validation is enabled."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="source",
            target_field="target",
        )

        # Valid assignment
        rule.priority = 500
        assert rule.priority == 500

        # Invalid assignment should raise
        with pytest.raises(ValidationError):
            rule.priority = 1001

    def test_use_enum_values_false(self):
        """Test use_enum_values=False preserves enum objects."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="source",
            target_field="target",
            mapping_type=EnumMappingType.TRANSFORM,
        )

        # Should be enum object, not string value
        assert isinstance(rule.mapping_type, EnumMappingType)
        assert rule.mapping_type == EnumMappingType.TRANSFORM
        assert rule.mapping_type.value == "transform"

    def test_model_serialization(self):
        """Test model can be serialized and deserialized."""
        original = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="input",
            target_field="output",
            mapping_type=EnumMappingType.CONDITIONAL,
            transformation_expression="{input}.upper()",
            default_value="N/A",
            is_required=True,
            apply_condition="input is not None",
            priority=250,
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize
        restored = ModelEventMappingRule(**data)

        assert restored.source_field == original.source_field
        assert restored.target_field == original.target_field
        assert restored.mapping_type == original.mapping_type
        assert restored.transformation_expression == original.transformation_expression
        assert restored.default_value == original.default_value
        assert restored.is_required == original.is_required
        assert restored.apply_condition == original.apply_condition
        assert restored.priority == original.priority

    def test_model_json_serialization(self):
        """Test model JSON serialization."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="field1",
            target_field="field2",
            mapping_type=EnumMappingType.DIRECT,
        )

        json_str = rule.model_dump_json()
        assert isinstance(json_str, str)
        assert "field1" in json_str
        assert "field2" in json_str

    def test_model_json_deserialization(self):
        """Test model JSON deserialization."""
        json_data = """{
            "version": {"major": 1, "minor": 0, "patch": 0},
            "source_field": "user_email",
            "target_field": "email",
            "mapping_type": "direct",
            "is_required": true,
            "priority": 200
        }"""

        rule = ModelEventMappingRule.model_validate_json(json_data)

        assert rule.source_field == "user_email"
        assert rule.target_field == "email"
        assert rule.mapping_type == EnumMappingType.DIRECT
        assert rule.is_required is True
        assert rule.priority == 200


@pytest.mark.unit
class TestModelEventMappingRuleDocumentation:
    """Test documentation and interface guarantees."""

    def test_docstring_present(self):
        """Test model has docstring."""
        assert ModelEventMappingRule.__doc__ is not None
        assert len(ModelEventMappingRule.__doc__) > 20

    def test_field_descriptions(self):
        """Test all fields have descriptions."""
        schema = ModelEventMappingRule.model_json_schema()

        for field_name, field_info in schema.get("properties", {}).items():
            assert "description" in field_info, (
                f"Field {field_name} missing description"
            )

    def test_required_fields_documented(self):
        """Test required fields are properly documented in schema."""
        schema = ModelEventMappingRule.model_json_schema()

        required_fields = schema.get("required", [])
        assert "source_field" in required_fields
        assert "target_field" in required_fields

    def test_optional_fields_documented(self):
        """Test optional fields are not in required list."""
        schema = ModelEventMappingRule.model_json_schema()

        required_fields = schema.get("required", [])
        assert "mapping_type" not in required_fields
        assert "transformation_expression" not in required_fields
        assert "default_value" not in required_fields
        assert "is_required" not in required_fields
        assert "apply_condition" not in required_fields
        assert "priority" not in required_fields


@pytest.mark.unit
class TestModelEventMappingRuleUseCases:
    """Test real-world use case scenarios."""

    def test_simple_field_rename(self):
        """Test simple field rename operation."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="userId",
            target_field="user_id",
            mapping_type=EnumMappingType.DIRECT,
        )

        assert rule.mapping_type == EnumMappingType.DIRECT
        assert rule.transformation_expression is None

    def test_timestamp_conversion(self):
        """Test timestamp format conversion."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="created_timestamp",
            target_field="created_at",
            mapping_type=EnumMappingType.TRANSFORM,
            transformation_expression="datetime.fromtimestamp({created_timestamp}/1000)",
            is_required=True,
        )

        assert rule.mapping_type == EnumMappingType.TRANSFORM
        assert rule.is_required is True

    def test_conditional_premium_discount(self):
        """Test conditional premium user discount."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="user_discount",
            target_field="final_discount",
            mapping_type=EnumMappingType.CONDITIONAL,
            apply_condition="user_type == 'premium'",
            transformation_expression="{user_discount} * 1.5",
            default_value="0.0",
        )

        assert rule.mapping_type == EnumMappingType.CONDITIONAL
        assert rule.apply_condition is not None
        assert rule.default_value == "0.0"

    def test_composite_full_name(self):
        """Test composite full name generation."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="first_name,last_name",
            target_field="full_name",
            mapping_type=EnumMappingType.COMPOSITE,
            transformation_expression="{first_name} {last_name}",
            is_required=True,
            priority=900,
        )

        assert rule.mapping_type == EnumMappingType.COMPOSITE
        assert rule.priority == 900

    def test_currency_conversion(self):
        """Test currency conversion mapping."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="price_eur",
            target_field="price_usd",
            mapping_type=EnumMappingType.TRANSFORM,
            transformation_expression="{price_eur} * 1.09",
            default_value="0.00",
        )

        assert rule.mapping_type == EnumMappingType.TRANSFORM
        assert rule.default_value == "0.00"

    def test_priority_ordering_critical_field(self):
        """Test high priority for critical field mapping."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="transaction_id",
            target_field="txn_id",
            mapping_type=EnumMappingType.DIRECT,
            is_required=True,
            priority=1000,
        )

        assert rule.priority == 1000
        assert rule.is_required is True

    def test_priority_ordering_optional_metadata(self):
        """Test low priority for optional metadata."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="extra_metadata",
            target_field="metadata",
            mapping_type=EnumMappingType.DIRECT,
            is_required=False,
            priority=10,
        )

        assert rule.priority == 10
        assert rule.is_required is False


@pytest.mark.unit
class TestModelEventMappingRuleDefaultValueTypes:
    """Test default_value field with multiple data types."""

    def test_default_value_string(self):
        """Test default_value with string type."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="status",
            target_field="order_status",
            default_value="pending",
        )

        assert rule.default_value == "pending"
        assert isinstance(rule.default_value, str)

    def test_default_value_integer(self):
        """Test default_value with integer type."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="count",
            target_field="item_count",
            default_value=0,
        )

        assert rule.default_value == 0
        assert isinstance(rule.default_value, int)

    def test_default_value_integer_positive(self):
        """Test default_value with positive integer."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="quantity",
            target_field="product_quantity",
            default_value=100,
        )

        assert rule.default_value == 100
        assert isinstance(rule.default_value, int)

    def test_default_value_integer_negative(self):
        """Test default_value with negative integer."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="balance",
            target_field="account_balance",
            default_value=-50,
        )

        assert rule.default_value == -50
        assert isinstance(rule.default_value, int)

    def test_default_value_float(self):
        """Test default_value with float type."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="price",
            target_field="product_price",
            default_value=0.0,
        )

        assert rule.default_value == 0.0
        assert isinstance(rule.default_value, float)

    def test_default_value_float_positive(self):
        """Test default_value with positive float."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="discount",
            target_field="discount_rate",
            default_value=15.5,
        )

        assert rule.default_value == 15.5
        assert isinstance(rule.default_value, float)

    def test_default_value_float_negative(self):
        """Test default_value with negative float."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="adjustment",
            target_field="price_adjustment",
            default_value=-9.99,
        )

        assert rule.default_value == -9.99
        assert isinstance(rule.default_value, float)

    def test_default_value_float_scientific_notation(self):
        """Test default_value with scientific notation float."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="epsilon",
            target_field="threshold",
            default_value=1e-6,
        )

        assert rule.default_value == 1e-6
        assert isinstance(rule.default_value, float)

    def test_default_value_boolean_true(self):
        """Test default_value with boolean True."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="is_active",
            target_field="active_status",
            default_value=True,
        )

        assert rule.default_value is True
        assert isinstance(rule.default_value, bool)

    def test_default_value_boolean_false(self):
        """Test default_value with boolean False."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="is_deleted",
            target_field="deleted_flag",
            default_value=False,
        )

        assert rule.default_value is False
        assert isinstance(rule.default_value, bool)

    def test_default_value_none(self):
        """Test default_value with None."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="optional",
            target_field="optional_field",
            default_value=None,
        )

        assert rule.default_value is None

    def test_default_value_empty_string(self):
        """Test default_value with empty string (backwards compatibility)."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="description",
            target_field="item_description",
            default_value="",
        )

        assert rule.default_value == ""
        assert isinstance(rule.default_value, str)

    def test_default_value_zero_integer(self):
        """Test default_value with zero integer."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="errors",
            target_field="error_count",
            default_value=0,
        )

        assert rule.default_value == 0
        assert isinstance(rule.default_value, int)
        # Ensure it's not treated as False (bool)
        assert rule.default_value is not False

    def test_default_value_zero_float(self):
        """Test default_value with zero float."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="tax",
            target_field="tax_amount",
            default_value=0.0,
        )

        assert rule.default_value == 0.0
        assert isinstance(rule.default_value, float)

    def test_default_value_mixed_types_serialization(self):
        """Test serialization/deserialization preserves type information."""
        test_cases = [
            ("string_field", "default_string", "default_string", str),
            ("int_field", 42, 42, int),
            ("float_field", 3.14, 3.14, float),
            ("bool_true_field", True, True, bool),
            ("bool_false_field", False, False, bool),
            ("none_field", None, None, type(None)),
        ]

        for source_field, default_value, expected_value, expected_type in test_cases:
            original = ModelEventMappingRule(
                version=DEFAULT_VERSION,
                source_field=source_field,
                target_field=f"target_{source_field}",
                default_value=default_value,
            )

            # Serialize to dict
            data = original.model_dump()

            # Deserialize
            restored = ModelEventMappingRule(**data)

            assert restored.default_value == expected_value
            if expected_type is not type(None):
                assert isinstance(restored.default_value, expected_type)

    def test_default_value_json_serialization_types(self):
        """Test JSON serialization preserves type information."""
        # Integer
        rule_int = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="count",
            target_field="total_count",
            default_value=100,
        )
        json_str = rule_int.model_dump_json()
        restored_int = ModelEventMappingRule.model_validate_json(json_str)
        assert restored_int.default_value == 100
        assert isinstance(restored_int.default_value, int)

        # Float
        rule_float = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="rate",
            target_field="conversion_rate",
            default_value=0.95,
        )
        json_str = rule_float.model_dump_json()
        restored_float = ModelEventMappingRule.model_validate_json(json_str)
        assert restored_float.default_value == 0.95
        assert isinstance(restored_float.default_value, float)

        # Boolean
        rule_bool = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="enabled",
            target_field="is_enabled",
            default_value=True,
        )
        json_str = rule_bool.model_dump_json()
        restored_bool = ModelEventMappingRule.model_validate_json(json_str)
        assert restored_bool.default_value is True
        assert isinstance(restored_bool.default_value, bool)

    def test_default_value_backwards_compatibility_strings(self):
        """Test backwards compatibility with existing string defaults."""
        # Existing test cases from TestModelEventMappingRuleEdgeCases
        # should still work with string default values
        test_cases = [
            "pending",
            "0",
            "0.0",
            "N/A",
            "",
            '{"status": "unknown", "code": 0}',
            "2024-01-01T00:00:00Z",
        ]

        for default_value in test_cases:
            rule = ModelEventMappingRule(
                version=DEFAULT_VERSION,
                source_field="test_field",
                target_field="target_field",
                default_value=default_value,
            )

            assert rule.default_value == default_value
            assert isinstance(rule.default_value, str)

    def test_default_value_use_case_counter(self):
        """Test use case: counter with integer default."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="retry_count",
            target_field="attempts",
            default_value=0,
            mapping_type=EnumMappingType.DIRECT,
        )

        assert rule.default_value == 0
        assert isinstance(rule.default_value, int)

    def test_default_value_use_case_percentage(self):
        """Test use case: percentage with float default."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="completion",
            target_field="completion_percentage",
            default_value=0.0,
            mapping_type=EnumMappingType.DIRECT,
        )

        assert rule.default_value == 0.0
        assert isinstance(rule.default_value, float)

    def test_default_value_use_case_feature_flag(self):
        """Test use case: feature flag with boolean default."""
        rule = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="experimental_feature",
            target_field="enable_experimental",
            default_value=False,
            mapping_type=EnumMappingType.DIRECT,
        )

        assert rule.default_value is False
        assert isinstance(rule.default_value, bool)

    def test_default_value_type_precision(self):
        """Test that numeric types maintain precision."""
        # Float precision
        rule_precision = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="pi",
            target_field="pi_value",
            default_value=3.14159265359,
        )

        assert rule_precision.default_value == 3.14159265359
        assert isinstance(rule_precision.default_value, float)

        # Large integer
        rule_large_int = ModelEventMappingRule(
            version=DEFAULT_VERSION,
            source_field="timestamp_ms",
            target_field="timestamp",
            default_value=1704067200000,  # 2024-01-01 in milliseconds
        )

        assert rule_large_int.default_value == 1704067200000
        assert isinstance(rule_large_int.default_value, int)
