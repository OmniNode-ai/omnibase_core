"""
Unit tests for ModelResponseHeaderRule - ONEX Standards Compliant.

Comprehensive test coverage for response header rule model including:
- Field validation and constraints
- Transformation type validation
- Cache control awareness
- Priority bounds and defaults
- Edge cases and error scenarios
- ConfigDict behavior
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)

from omnibase_core.models.contracts.subcontracts.model_response_header_rule import (
    ModelResponseHeaderRule,
)


class TestModelResponseHeaderRuleBasics:
    """Test basic model instantiation and defaults."""

    def test_minimal_instantiation(self):
        """Test model can be instantiated with minimal required fields."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Response-Time",
            transformation_rule="{response_time_ms}",
        )

        assert rule.header_name == "X-Response-Time"
        assert rule.transformation_rule == "{response_time_ms}"
        assert rule.transformation_type == "set"
        assert rule.apply_condition is None
        assert rule.case_sensitive is True
        assert rule.expose_to_client is True
        assert rule.cache_control_aware is False
        assert rule.priority == 100

    def test_full_instantiation(self):
        """Test model with all fields specified."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="Cache-Control",
            transformation_rule="max-age=3600, public",
            transformation_type="append",
            apply_condition="response.status == 200",
            case_sensitive=False,
            expose_to_client=False,
            cache_control_aware=True,
            priority=500,
        )

        assert rule.header_name == "Cache-Control"
        assert rule.transformation_rule == "max-age=3600, public"
        assert rule.transformation_type == "append"
        assert rule.apply_condition == "response.status == 200"
        assert rule.case_sensitive is False
        assert rule.expose_to_client is False
        assert rule.cache_control_aware is True
        assert rule.priority == 500

    def test_default_values(self):
        """Test default values are correctly applied."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Header",
            transformation_rule="value",
        )

        # Defaults from model
        assert rule.transformation_type == "set"
        assert rule.apply_condition is None
        assert rule.case_sensitive is True
        assert rule.expose_to_client is True
        assert rule.cache_control_aware is False
        assert rule.priority == 100


class TestModelResponseHeaderRuleValidation:
    """Test field validation and constraints."""

    def test_header_name_required(self):
        """Test header_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelResponseHeaderRule(
                version=DEFAULT_VERSION,
                transformation_rule="value",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("header_name",) for e in errors)

    def test_header_name_min_length(self):
        """Test header_name must have minimum length."""
        # Empty string should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelResponseHeaderRule(
                version=DEFAULT_VERSION,
                header_name="",
                transformation_rule="value",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("header_name",) for e in errors)

    def test_header_name_valid_values(self):
        """Test various valid response header names."""
        valid_names = [
            "Content-Type",
            "X-Response-Time",
            "Cache-Control",
            "ETag",
            "X-Request-ID",
            "X-RateLimit-Remaining",
            "Access-Control-Allow-Origin",
            "Set-Cookie",
        ]

        for name in valid_names:
            rule = ModelResponseHeaderRule(
                version=DEFAULT_VERSION,
                header_name=name,
                transformation_rule="value",
            )
            assert rule.header_name == name

    def test_transformation_rule_required(self):
        """Test transformation_rule is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelResponseHeaderRule(
                version=DEFAULT_VERSION,
                header_name="X-Custom-Header",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("transformation_rule",) for e in errors)

    def test_transformation_rule_min_length(self):
        """Test transformation_rule must have minimum length."""
        # Empty string should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelResponseHeaderRule(
                version=DEFAULT_VERSION,
                header_name="X-Custom-Header",
                transformation_rule="",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("transformation_rule",) for e in errors)

    def test_transformation_type_valid_values(self):
        """Test various valid transformation types."""
        valid_types = ["set", "append", "prefix", "suffix", "remove", "filter"]

        for trans_type in valid_types:
            rule = ModelResponseHeaderRule(
                version=DEFAULT_VERSION,
                header_name="X-Custom-Header",
                transformation_rule="value",
                transformation_type=trans_type,
            )
            assert rule.transformation_type == trans_type

    def test_transformation_type_default(self):
        """Test transformation_type defaults to 'set'."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Header",
            transformation_rule="value",
        )

        assert rule.transformation_type == "set"

    def test_priority_bounds(self):
        """Test priority validates bounds."""
        # Valid values
        ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Header",
            transformation_rule="value",
            priority=0,  # Min
        )
        ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Header",
            transformation_rule="value",
            priority=500,
        )
        ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Header",
            transformation_rule="value",
            priority=1000,  # Max
        )

        # Below minimum
        with pytest.raises(ValidationError) as exc_info:
            ModelResponseHeaderRule(
                version=DEFAULT_VERSION,
                header_name="X-Custom-Header",
                transformation_rule="value",
                priority=-1,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("priority",) for e in errors)

        # Above maximum
        with pytest.raises(ValidationError) as exc_info:
            ModelResponseHeaderRule(
                version=DEFAULT_VERSION,
                header_name="X-Custom-Header",
                transformation_rule="value",
                priority=1001,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("priority",) for e in errors)

    def test_case_sensitive_boolean(self):
        """Test case_sensitive accepts boolean values."""
        rule_true = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Header",
            transformation_rule="value",
            case_sensitive=True,
        )
        assert rule_true.case_sensitive is True

        rule_false = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Header",
            transformation_rule="value",
            case_sensitive=False,
        )
        assert rule_false.case_sensitive is False

    def test_expose_to_client_boolean(self):
        """Test expose_to_client accepts boolean values."""
        rule_true = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Public-Header",
            transformation_rule="value",
            expose_to_client=True,
        )
        assert rule_true.expose_to_client is True

        rule_false = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Internal-Header",
            transformation_rule="value",
            expose_to_client=False,
        )
        assert rule_false.expose_to_client is False

    def test_cache_control_aware_boolean(self):
        """Test cache_control_aware accepts boolean values."""
        rule_true = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="Cache-Control",
            transformation_rule="max-age=3600",
            cache_control_aware=True,
        )
        assert rule_true.cache_control_aware is True

        rule_false = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Header",
            transformation_rule="value",
            cache_control_aware=False,
        )
        assert rule_false.cache_control_aware is False

    def test_apply_condition_optional(self):
        """Test apply_condition is optional."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Header",
            transformation_rule="value",
            apply_condition=None,
        )
        assert rule.apply_condition is None

        rule_with_condition = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Header",
            transformation_rule="value",
            apply_condition="response.status == 200",
        )
        assert rule_with_condition.apply_condition == "response.status == 200"


class TestModelResponseHeaderRuleEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_minimum_priority_rule(self):
        """Test rule with minimum priority."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Low-Priority",
            transformation_rule="value",
            priority=0,
        )

        assert rule.priority == 0

    def test_maximum_priority_rule(self):
        """Test rule with maximum priority."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-High-Priority",
            transformation_rule="value",
            priority=1000,
        )

        assert rule.priority == 1000

    def test_set_transformation(self):
        """Test 'set' transformation type."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="Content-Type",
            transformation_rule="application/json",
            transformation_type="set",
        )

        assert rule.transformation_type == "set"

    def test_append_transformation(self):
        """Test 'append' transformation type."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="Cache-Control",
            transformation_rule=", must-revalidate",
            transformation_type="append",
        )

        assert rule.transformation_type == "append"

    def test_prefix_transformation(self):
        """Test 'prefix' transformation type."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Value",
            transformation_rule="prefix_",
            transformation_type="prefix",
        )

        assert rule.transformation_type == "prefix"

    def test_suffix_transformation(self):
        """Test 'suffix' transformation type."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Version",
            transformation_rule="_v2",
            transformation_type="suffix",
        )

        assert rule.transformation_type == "suffix"

    def test_remove_transformation(self):
        """Test 'remove' transformation type."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Sensitive-Header",
            transformation_rule="N/A",  # Not used for remove, but required by validation
            transformation_type="remove",
        )

        assert rule.transformation_type == "remove"

    def test_filter_transformation(self):
        """Test 'filter' transformation type."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="Set-Cookie",
            transformation_rule="filter_pattern",
            transformation_type="filter",
        )

        assert rule.transformation_type == "filter"

    def test_cache_control_header_transformation(self):
        """Test transformation specifically for Cache-Control header."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="Cache-Control",
            transformation_rule="max-age=3600, public",
            cache_control_aware=True,
        )

        assert rule.header_name == "Cache-Control"
        assert rule.cache_control_aware is True

    def test_cors_header_transformation(self):
        """Test transformation for CORS headers."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="Access-Control-Allow-Origin",
            transformation_rule="*",
            expose_to_client=True,
        )

        assert rule.header_name == "Access-Control-Allow-Origin"
        assert rule.expose_to_client is True

    def test_internal_header_not_exposed(self):
        """Test internal header not exposed to client."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Internal-Processing-Time",
            transformation_rule="{internal_time}",
            expose_to_client=False,
        )

        assert rule.expose_to_client is False

    def test_template_transformation_rule(self):
        """Test transformation rule with template variables."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Request-ID",
            transformation_rule="{request.id}",
        )

        assert "{request.id}" in rule.transformation_rule

    def test_complex_apply_condition(self):
        """Test complex apply condition."""
        condition = "(response.status >= 200 and response.status < 300) or response.headers.get('X-Force-Transform')"
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Success-Header",
            transformation_rule="success",
            apply_condition=condition,
        )

        assert rule.apply_condition == condition

    def test_case_insensitive_header_matching(self):
        """Test case-insensitive header matching configuration."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="content-type",  # Lowercase
            transformation_rule="application/json",
            case_sensitive=False,
        )

        assert rule.case_sensitive is False

    def test_rate_limit_headers(self):
        """Test transformation for rate limit headers."""
        rules = [
            ModelResponseHeaderRule(
                version=DEFAULT_VERSION,
                header_name="X-RateLimit-Limit",
                transformation_rule="1000",
            ),
            ModelResponseHeaderRule(
                version=DEFAULT_VERSION,
                header_name="X-RateLimit-Remaining",
                transformation_rule="{remaining}",
            ),
            ModelResponseHeaderRule(
                version=DEFAULT_VERSION,
                header_name="X-RateLimit-Reset",
                transformation_rule="{reset_time}",
            ),
        ]

        assert len(rules) == 3
        assert all(rule.header_name.startswith("X-RateLimit-") for rule in rules)

    def test_multiple_rules_same_header_different_priorities(self):
        """Test multiple rules for same header with different priorities."""
        rule1 = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="Cache-Control",
            transformation_rule="no-cache",
            priority=100,
        )

        rule2 = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="Cache-Control",
            transformation_rule="max-age=3600",
            priority=200,
        )

        assert rule1.header_name == rule2.header_name
        assert rule1.priority < rule2.priority


class TestModelResponseHeaderRuleConfigDict:
    """Test ConfigDict behavior."""

    def test_extra_fields_ignored(self):
        """Test extra fields are ignored per ConfigDict."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Header",
            transformation_rule="value",
            unknown_field="should_be_ignored",  # type: ignore[call-arg]
        )

        assert rule.header_name == "X-Custom-Header"
        assert not hasattr(rule, "unknown_field")

    def test_validate_assignment(self):
        """Test assignment validation is enabled."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Header",
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
        original = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="Cache-Control",
            transformation_rule="max-age=3600, public",
            transformation_type="append",
            apply_condition="response.status == 200",
            case_sensitive=False,
            expose_to_client=True,
            cache_control_aware=True,
            priority=750,
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize
        restored = ModelResponseHeaderRule(**data)

        assert restored.header_name == original.header_name
        assert restored.transformation_rule == original.transformation_rule
        assert restored.transformation_type == original.transformation_type
        assert restored.apply_condition == original.apply_condition
        assert restored.case_sensitive == original.case_sensitive
        assert restored.expose_to_client == original.expose_to_client
        assert restored.cache_control_aware == original.cache_control_aware
        assert restored.priority == original.priority

    def test_json_serialization(self):
        """Test model can be serialized to JSON."""
        rule = ModelResponseHeaderRule(
            version=DEFAULT_VERSION,
            header_name="Content-Type",
            transformation_rule="application/json",
        )

        json_str = rule.model_dump_json()
        assert "Content-Type" in json_str
        assert "application/json" in json_str


class TestModelResponseHeaderRuleDocumentation:
    """Test documentation and interface guarantees."""

    def test_docstring_present(self):
        """Test model has comprehensive docstring."""
        assert ModelResponseHeaderRule.__doc__ is not None
        assert len(ModelResponseHeaderRule.__doc__) > 50

    def test_field_descriptions(self):
        """Test all fields have descriptions."""
        schema = ModelResponseHeaderRule.model_json_schema()

        for field_name, field_info in schema.get("properties", {}).items():
            assert "description" in field_info, (
                f"Field {field_name} missing description"
            )
