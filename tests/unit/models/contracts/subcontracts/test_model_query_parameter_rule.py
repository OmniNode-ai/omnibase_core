"""
Unit tests for ModelQueryParameterRule.

Comprehensive test coverage for query parameter rule model including:
- Field validation and constraints
- Transformation type validation
- URL encoding behavior
- Priority bounds and defaults
- Edge cases and error scenarios
- ConfigDict behavior
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)

from omnibase_core.models.contracts.subcontracts.model_query_parameter_rule import (
    ModelQueryParameterRule,
)


@pytest.mark.unit
class TestModelQueryParameterRuleBasics:
    """Test basic model instantiation and defaults."""

    def test_minimal_instantiation(self):
        """Test model can be instantiated with minimal required fields."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="user_id",
            transformation_rule="12345",
        )

        assert rule.parameter_name == "user_id"
        assert rule.transformation_rule == "12345"
        assert rule.transformation_type == "set"
        assert rule.apply_condition is None
        assert rule.case_sensitive is True
        assert rule.url_encode is True
        assert rule.priority == 100

    def test_full_instantiation(self):
        """Test model with all fields specified."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="api_key",
            transformation_rule="{user.api_key}",
            transformation_type="prefix",
            apply_condition="request.auth.is_authenticated",
            case_sensitive=False,
            url_encode=False,
            priority=500,
        )

        assert rule.parameter_name == "api_key"
        assert rule.transformation_rule == "{user.api_key}"
        assert rule.transformation_type == "prefix"
        assert rule.apply_condition == "request.auth.is_authenticated"
        assert rule.case_sensitive is False
        assert rule.url_encode is False
        assert rule.priority == 500

    def test_default_values(self):
        """Test default values are correctly applied."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="test_param",
            transformation_rule="test_value",
        )

        # Defaults from model
        assert rule.transformation_type == "set"
        assert rule.apply_condition is None
        assert rule.case_sensitive is True
        assert rule.url_encode is True
        assert rule.priority == 100


@pytest.mark.unit
class TestModelQueryParameterRuleValidation:
    """Test field validation and constraints."""

    def test_parameter_name_required(self):
        """Test parameter_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelQueryParameterRule(
                version=DEFAULT_VERSION,
                transformation_rule="value",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("parameter_name",) for e in errors)

    def test_parameter_name_min_length(self):
        """Test parameter_name must have minimum length."""
        # Empty string should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelQueryParameterRule(
                version=DEFAULT_VERSION,
                parameter_name="",
                transformation_rule="value",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("parameter_name",) for e in errors)

    def test_parameter_name_valid_values(self):
        """Test various valid parameter names."""
        valid_names = [
            "id",
            "user_id",
            "api_key",
            "page",
            "limit",
            "sort",
            "filter",
            "search_query",
        ]

        for name in valid_names:
            rule = ModelQueryParameterRule(
                version=DEFAULT_VERSION,
                parameter_name=name,
                transformation_rule="value",
            )
            assert rule.parameter_name == name

    def test_transformation_rule_required(self):
        """Test transformation_rule is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelQueryParameterRule(
                version=DEFAULT_VERSION,
                parameter_name="test_param",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("transformation_rule",) for e in errors)

    def test_transformation_rule_min_length(self):
        """Test transformation_rule must have minimum length."""
        # Empty string should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelQueryParameterRule(
                version=DEFAULT_VERSION,
                parameter_name="test_param",
                transformation_rule="",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("transformation_rule",) for e in errors)

    def test_transformation_type_valid_values(self):
        """Test various valid transformation types."""
        valid_types = ["set", "append", "prefix", "suffix", "remove", "encode"]

        for trans_type in valid_types:
            rule = ModelQueryParameterRule(
                version=DEFAULT_VERSION,
                parameter_name="test_param",
                transformation_rule="value",
                transformation_type=trans_type,
            )
            assert rule.transformation_type == trans_type

    def test_transformation_type_default(self):
        """Test transformation_type defaults to 'set'."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="test_param",
            transformation_rule="value",
        )

        assert rule.transformation_type == "set"

    def test_priority_bounds(self):
        """Test priority validates bounds."""
        # Valid values
        ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="test_param",
            transformation_rule="value",
            priority=0,  # Min
        )
        ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="test_param",
            transformation_rule="value",
            priority=500,
        )
        ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="test_param",
            transformation_rule="value",
            priority=1000,  # Max
        )

        # Below minimum
        with pytest.raises(ValidationError) as exc_info:
            ModelQueryParameterRule(
                version=DEFAULT_VERSION,
                parameter_name="test_param",
                transformation_rule="value",
                priority=-1,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("priority",) for e in errors)

        # Above maximum
        with pytest.raises(ValidationError) as exc_info:
            ModelQueryParameterRule(
                version=DEFAULT_VERSION,
                parameter_name="test_param",
                transformation_rule="value",
                priority=1001,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("priority",) for e in errors)

    def test_case_sensitive_boolean(self):
        """Test case_sensitive accepts boolean values."""
        rule_true = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="test_param",
            transformation_rule="value",
            case_sensitive=True,
        )
        assert rule_true.case_sensitive is True

        rule_false = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="test_param",
            transformation_rule="value",
            case_sensitive=False,
        )
        assert rule_false.case_sensitive is False

    def test_url_encode_boolean(self):
        """Test url_encode accepts boolean values."""
        rule_true = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="test_param",
            transformation_rule="value with spaces",
            url_encode=True,
        )
        assert rule_true.url_encode is True

        rule_false = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="test_param",
            transformation_rule="value",
            url_encode=False,
        )
        assert rule_false.url_encode is False

    def test_apply_condition_optional(self):
        """Test apply_condition is optional."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="test_param",
            transformation_rule="value",
            apply_condition=None,
        )
        assert rule.apply_condition is None

        rule_with_condition = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="test_param",
            transformation_rule="value",
            apply_condition="request.method == 'GET'",
        )
        assert rule_with_condition.apply_condition == "request.method == 'GET'"


@pytest.mark.unit
class TestModelQueryParameterRuleEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_minimum_priority_rule(self):
        """Test rule with minimum priority."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="low_priority_param",
            transformation_rule="value",
            priority=0,
        )

        assert rule.priority == 0

    def test_maximum_priority_rule(self):
        """Test rule with maximum priority."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="high_priority_param",
            transformation_rule="value",
            priority=1000,
        )

        assert rule.priority == 1000

    def test_set_transformation(self):
        """Test 'set' transformation type."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="status",
            transformation_rule="active",
            transformation_type="set",
        )

        assert rule.transformation_type == "set"

    def test_append_transformation(self):
        """Test 'append' transformation type."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="tags",
            transformation_rule=",new_tag",
            transformation_type="append",
        )

        assert rule.transformation_type == "append"

    def test_prefix_transformation(self):
        """Test 'prefix' transformation type."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="search",
            transformation_rule="prefix_",
            transformation_type="prefix",
        )

        assert rule.transformation_type == "prefix"

    def test_suffix_transformation(self):
        """Test 'suffix' transformation type."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="version",
            transformation_rule="_latest",
            transformation_type="suffix",
        )

        assert rule.transformation_type == "suffix"

    def test_remove_transformation(self):
        """Test 'remove' transformation type."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="sensitive_param",
            transformation_rule="N/A",  # Not used for remove, but required by validation
            transformation_type="remove",
        )

        assert rule.transformation_type == "remove"

    def test_encode_transformation(self):
        """Test 'encode' transformation type."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="query",
            transformation_rule="search term with spaces",
            transformation_type="encode",
        )

        assert rule.transformation_type == "encode"

    def test_template_transformation_rule(self):
        """Test transformation rule with template variables."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="user",
            transformation_rule="{user.username}",
        )

        assert "{user.username}" in rule.transformation_rule

    def test_special_characters_in_transformation_rule(self):
        """Test transformation rule with special characters requiring encoding."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="query",
            transformation_rule="hello world & foo=bar",
            url_encode=True,
        )

        assert rule.url_encode is True
        assert "&" in rule.transformation_rule

    def test_url_encoding_disabled(self):
        """Test URL encoding can be disabled."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="raw_value",
            transformation_rule="already%20encoded",
            url_encode=False,
        )

        assert rule.url_encode is False

    def test_complex_apply_condition(self):
        """Test complex apply condition."""
        condition = "(request.path == '/search' and 'query' in request.params) or request.headers.get('X-Force-Transform')"
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="search_param",
            transformation_rule="value",
            apply_condition=condition,
        )

        assert rule.apply_condition == condition

    def test_case_insensitive_parameter_matching(self):
        """Test case-insensitive parameter matching configuration."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="userid",  # Lowercase
            transformation_rule="12345",
            case_sensitive=False,
        )

        assert rule.case_sensitive is False

    def test_multiple_rules_same_parameter_different_priorities(self):
        """Test multiple rules for same parameter with different priorities."""
        rule1 = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="page",
            transformation_rule="1",
            priority=100,
        )

        rule2 = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="page",
            transformation_rule="10",
            priority=200,
        )

        assert rule1.parameter_name == rule2.parameter_name
        assert rule1.priority < rule2.priority


@pytest.mark.unit
class TestModelQueryParameterRuleConfigDict:
    """Test ConfigDict behavior."""

    def test_extra_fields_ignored(self):
        """Test extra fields are ignored per ConfigDict."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="test_param",
            transformation_rule="value",
            unknown_field="should_be_ignored",  # type: ignore[call-arg]
        )

        assert rule.parameter_name == "test_param"
        assert not hasattr(rule, "unknown_field")

    def test_validate_assignment(self):
        """Test assignment validation is enabled."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="test_param",
            transformation_rule="value",
        )

        # Valid assignment
        rule.priority = 500
        assert rule.priority == 500

        # Invalid assignment should raise
        with pytest.raises(ValidationError):
            rule.priority = -1

        with pytest.raises(ValidationError):
            rule.priority = 1001

    def test_model_serialization(self):
        """Test model can be serialized and deserialized."""
        original = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="api_key",
            transformation_rule="{user.api_key}",
            transformation_type="prefix",
            apply_condition="request.auth.is_authenticated",
            case_sensitive=False,
            url_encode=False,
            priority=750,
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize
        restored = ModelQueryParameterRule(**data)

        assert restored.parameter_name == original.parameter_name
        assert restored.transformation_rule == original.transformation_rule
        assert restored.transformation_type == original.transformation_type
        assert restored.apply_condition == original.apply_condition
        assert restored.case_sensitive == original.case_sensitive
        assert restored.url_encode == original.url_encode
        assert restored.priority == original.priority

    def test_json_serialization(self):
        """Test model can be serialized to JSON."""
        rule = ModelQueryParameterRule(
            version=DEFAULT_VERSION,
            parameter_name="user_id",
            transformation_rule="12345",
        )

        json_str = rule.model_dump_json()
        assert "user_id" in json_str
        assert "12345" in json_str


@pytest.mark.unit
class TestModelQueryParameterRuleDocumentation:
    """Test documentation and interface guarantees."""

    def test_docstring_present(self):
        """Test model has comprehensive docstring."""
        assert ModelQueryParameterRule.__doc__ is not None
        assert len(ModelQueryParameterRule.__doc__) > 50

    def test_field_descriptions(self):
        """Test all fields have descriptions."""
        schema = ModelQueryParameterRule.model_json_schema()

        for field_name, field_info in schema.get("properties", {}).items():
            assert "description" in field_info, (
                f"Field {field_name} missing description"
            )
