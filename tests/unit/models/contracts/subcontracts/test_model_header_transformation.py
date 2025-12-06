"""
Unit tests for ModelHeaderTransformation - ONEX Standards Compliant.

Comprehensive test coverage for header transformation model including:
- Field validation and constraints
- Transformation type validation
- Priority bounds and defaults
- Edge cases and error scenarios
- ConfigDict behavior
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)

from omnibase_core.models.contracts.subcontracts.model_header_transformation import (
    ModelHeaderTransformation,
)


class TestModelHeaderTransformationBasics:
    """Test basic model instantiation and defaults."""

    def test_minimal_instantiation(self):
        """Test model can be instantiated with minimal required fields."""
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Header",
            transformation_rule="value123",
        )

        assert transform.header_name == "X-Custom-Header"
        assert transform.transformation_rule == "value123"
        assert transform.transformation_type == "set"
        assert transform.apply_condition is None
        assert transform.case_sensitive is True
        assert transform.priority == 100

    def test_full_instantiation(self):
        """Test model with all fields specified."""
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Authorization",
            transformation_rule="Bearer {token}",
            transformation_type="prefix",
            apply_condition="request.path.startswith('/api')",
            case_sensitive=False,
            priority=500,
        )

        assert transform.header_name == "Authorization"
        assert transform.transformation_rule == "Bearer {token}"
        assert transform.transformation_type == "prefix"
        assert transform.apply_condition == "request.path.startswith('/api')"
        assert transform.case_sensitive is False
        assert transform.priority == 500

    def test_default_values(self):
        """Test default values are correctly applied."""
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Test-Header",
            transformation_rule="test-value",
        )

        # Defaults from model
        assert transform.transformation_type == "set"
        assert transform.apply_condition is None
        assert transform.case_sensitive is True
        assert transform.priority == 100


class TestModelHeaderTransformationValidation:
    """Test field validation and constraints."""

    def test_header_name_required(self):
        """Test header_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHeaderTransformation(
                version=DEFAULT_VERSION,
                transformation_rule="value",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("header_name",) for e in errors)

    def test_header_name_min_length(self):
        """Test header_name must have minimum length."""
        # Empty string should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelHeaderTransformation(
                version=DEFAULT_VERSION,
                header_name="",
                transformation_rule="value",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("header_name",) for e in errors)

    def test_header_name_valid_values(self):
        """Test various valid header names."""
        valid_names = [
            "Content-Type",
            "X-Custom-Header",
            "Authorization",
            "Accept",
            "X-Request-ID",
            "Cache-Control",
            "X-Forwarded-For",
        ]

        for name in valid_names:
            transform = ModelHeaderTransformation(
                version=DEFAULT_VERSION,
                header_name=name,
                transformation_rule="value",
            )
            assert transform.header_name == name

    def test_transformation_rule_required(self):
        """Test transformation_rule is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHeaderTransformation(
                version=DEFAULT_VERSION,
                header_name="Test-Header",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("transformation_rule",) for e in errors)

    def test_transformation_rule_min_length(self):
        """Test transformation_rule must have minimum length."""
        # Empty string should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelHeaderTransformation(
                version=DEFAULT_VERSION,
                header_name="Test-Header",
                transformation_rule="",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("transformation_rule",) for e in errors)

    def test_transformation_type_valid_values(self):
        """Test various valid transformation types."""
        valid_types = ["set", "append", "prefix", "suffix", "remove"]

        for trans_type in valid_types:
            transform = ModelHeaderTransformation(
                version=DEFAULT_VERSION,
                header_name="Test-Header",
                transformation_rule="value",
                transformation_type=trans_type,
            )
            assert transform.transformation_type == trans_type

    def test_transformation_type_default(self):
        """Test transformation_type defaults to 'set'."""
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Test-Header",
            transformation_rule="value",
        )

        assert transform.transformation_type == "set"

    def test_priority_bounds(self):
        """Test priority validates bounds."""
        # Valid values
        ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Test-Header",
            transformation_rule="value",
            priority=0,  # Min
        )
        ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Test-Header",
            transformation_rule="value",
            priority=500,
        )
        ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Test-Header",
            transformation_rule="value",
            priority=1000,  # Max
        )

        # Below minimum
        with pytest.raises(ValidationError) as exc_info:
            ModelHeaderTransformation(
                version=DEFAULT_VERSION,
                header_name="Test-Header",
                transformation_rule="value",
                priority=-1,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("priority",) for e in errors)

        # Above maximum
        with pytest.raises(ValidationError) as exc_info:
            ModelHeaderTransformation(
                version=DEFAULT_VERSION,
                header_name="Test-Header",
                transformation_rule="value",
                priority=1001,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("priority",) for e in errors)

    def test_case_sensitive_boolean(self):
        """Test case_sensitive accepts boolean values."""
        transform_true = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Test-Header",
            transformation_rule="value",
            case_sensitive=True,
        )
        assert transform_true.case_sensitive is True

        transform_false = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Test-Header",
            transformation_rule="value",
            case_sensitive=False,
        )
        assert transform_false.case_sensitive is False

    def test_apply_condition_optional(self):
        """Test apply_condition is optional."""
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Test-Header",
            transformation_rule="value",
            apply_condition=None,
        )
        assert transform.apply_condition is None

        transform_with_condition = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Test-Header",
            transformation_rule="value",
            apply_condition="request.method == 'GET'",
        )
        assert transform_with_condition.apply_condition == "request.method == 'GET'"


class TestModelHeaderTransformationEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_minimum_priority_transform(self):
        """Test transformation with minimum priority."""
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Low-Priority-Header",
            transformation_rule="value",
            priority=0,
        )

        assert transform.priority == 0

    def test_maximum_priority_transform(self):
        """Test transformation with maximum priority."""
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="High-Priority-Header",
            transformation_rule="value",
            priority=1000,
        )

        assert transform.priority == 1000

    def test_set_transformation(self):
        """Test 'set' transformation type."""
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Content-Type",
            transformation_rule="application/json",
            transformation_type="set",
        )

        assert transform.transformation_type == "set"

    def test_append_transformation(self):
        """Test 'append' transformation type."""
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Header",
            transformation_rule="; extra=value",
            transformation_type="append",
        )

        assert transform.transformation_type == "append"

    def test_prefix_transformation(self):
        """Test 'prefix' transformation type."""
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Authorization",
            transformation_rule="Bearer ",
            transformation_type="prefix",
        )

        assert transform.transformation_type == "prefix"

    def test_suffix_transformation(self):
        """Test 'suffix' transformation type."""
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="User-Agent",
            transformation_rule=" (Custom)",
            transformation_type="suffix",
        )

        assert transform.transformation_type == "suffix"

    def test_remove_transformation(self):
        """Test 'remove' transformation type."""
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="X-Sensitive-Header",
            transformation_rule="N/A",  # Not used for remove, but required by validation
            transformation_type="remove",
        )

        assert transform.transformation_type == "remove"

    def test_template_transformation_rule(self):
        """Test transformation rule with template variables."""
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Authorization",
            transformation_rule="Bearer {jwt_token}",
        )

        assert "{jwt_token}" in transform.transformation_rule

    def test_complex_apply_condition(self):
        """Test complex apply condition."""
        condition = "(request.path.startswith('/api') and request.method == 'POST') or request.headers.get('X-Force-Transform')"
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Header",
            transformation_rule="value",
            apply_condition=condition,
        )

        assert transform.apply_condition == condition

    def test_case_insensitive_header_matching(self):
        """Test case-insensitive header matching configuration."""
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="content-type",  # Lowercase
            transformation_rule="application/json",
            case_sensitive=False,
        )

        assert transform.case_sensitive is False

    def test_multiple_transforms_same_header_different_priorities(self):
        """Test multiple transforms for same header with different priorities."""
        transform1 = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Header",
            transformation_rule="value1",
            priority=100,
        )

        transform2 = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="X-Custom-Header",
            transformation_rule="value2",
            priority=200,
        )

        assert transform1.header_name == transform2.header_name
        assert transform1.priority < transform2.priority


class TestModelHeaderTransformationConfigDict:
    """Test ConfigDict behavior."""

    def test_extra_fields_ignored(self):
        """Test extra fields are ignored per ConfigDict."""
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Test-Header",
            transformation_rule="value",
            unknown_field="should_be_ignored",  # type: ignore[call-arg]
        )

        assert transform.header_name == "Test-Header"
        assert not hasattr(transform, "unknown_field")

    def test_validate_assignment(self):
        """Test assignment validation is enabled."""
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Test-Header",
            transformation_rule="value",
        )

        # Valid assignment
        transform.priority = 500
        assert transform.priority == 500

        # Invalid assignment should raise
        with pytest.raises(ValidationError):
            transform.priority = -1

        with pytest.raises(ValidationError):
            transform.priority = 1001

    def test_model_serialization(self):
        """Test model can be serialized and deserialized."""
        original = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Authorization",
            transformation_rule="Bearer {token}",
            transformation_type="prefix",
            apply_condition="request.path.startswith('/secure')",
            case_sensitive=False,
            priority=750,
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize
        restored = ModelHeaderTransformation(**data)

        assert restored.header_name == original.header_name
        assert restored.transformation_rule == original.transformation_rule
        assert restored.transformation_type == original.transformation_type
        assert restored.apply_condition == original.apply_condition
        assert restored.case_sensitive == original.case_sensitive
        assert restored.priority == original.priority

    def test_json_serialization(self):
        """Test model can be serialized to JSON."""
        transform = ModelHeaderTransformation(
            version=DEFAULT_VERSION,
            header_name="Content-Type",
            transformation_rule="application/json",
        )

        json_str = transform.model_dump_json()
        assert "Content-Type" in json_str
        assert "application/json" in json_str


class TestModelHeaderTransformationDocumentation:
    """Test documentation and interface guarantees."""

    def test_docstring_present(self):
        """Test model has comprehensive docstring."""
        assert ModelHeaderTransformation.__doc__ is not None
        assert len(ModelHeaderTransformation.__doc__) > 50

    def test_field_descriptions(self):
        """Test all fields have descriptions."""
        schema = ModelHeaderTransformation.model_json_schema()

        for field_name, field_info in schema.get("properties", {}).items():
            assert "description" in field_info, (
                f"Field {field_name} missing description"
            )
