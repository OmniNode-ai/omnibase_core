"""
Unit tests for ModelBaseHeaderTransformation - ONEX Standards Compliant.

Comprehensive test coverage for base transformation model including:
- Field validation and constraints
- Priority bounds and defaults
- Edge cases and error scenarios
- Inheritance behavior
- ConfigDict behavior
"""

import pytest
from pydantic import Field, ValidationError

from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)

from omnibase_core.models.contracts.subcontracts.model_base_header_transformation import (
    ModelBaseHeaderTransformation,
)


# Create a concrete subclass for testing purposes
class ConcreteTransformation(ModelBaseHeaderTransformation):
    """Concrete implementation for testing base class."""

    name: str = Field(..., min_length=1)


class TestBaseHeaderTransformationBasics:
    """Test basic model instantiation and defaults."""

    def test_minimal_instantiation_via_subclass(self):
        """Test base class fields can be instantiated via subclass."""
        transform = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="test-rule",
        )

        assert transform.name == "test-name"
        assert transform.transformation_rule == "test-rule"
        assert transform.apply_condition is None
        assert transform.case_sensitive is True
        assert transform.priority == 100

    def test_full_instantiation_via_subclass(self):
        """Test base class with all fields specified via subclass."""
        transform = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="test-rule",
            apply_condition="condition",
            case_sensitive=False,
            priority=500,
        )

        assert transform.name == "test-name"
        assert transform.transformation_rule == "test-rule"
        assert transform.apply_condition == "condition"
        assert transform.case_sensitive is False
        assert transform.priority == 500

    def test_default_values(self):
        """Test default values are correctly applied."""
        transform = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="test-rule",
        )

        # Defaults from base class
        assert transform.apply_condition is None
        assert transform.case_sensitive is True
        assert transform.priority == 100


class TestBaseHeaderTransformationValidation:
    """Test field validation and constraints."""

    def test_transformation_rule_required(self):
        """Test transformation_rule is required."""
        with pytest.raises(ValidationError) as exc_info:
            ConcreteTransformation(
                version=DEFAULT_VERSION,
                name="test-name",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("transformation_rule",) for e in errors)

    def test_transformation_rule_min_length(self):
        """Test transformation_rule must have minimum length."""
        # Empty string should fail
        with pytest.raises(ValidationError) as exc_info:
            ConcreteTransformation(
                version=DEFAULT_VERSION,
                name="test-name",
                transformation_rule="",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("transformation_rule",) for e in errors)

    def test_priority_bounds(self):
        """Test priority validates bounds."""
        # Valid values
        ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="rule",
            priority=0,  # Min
        )
        ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="rule",
            priority=500,
        )
        ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="rule",
            priority=1000,  # Max
        )

        # Below minimum
        with pytest.raises(ValidationError) as exc_info:
            ConcreteTransformation(
                version=DEFAULT_VERSION,
                name="test-name",
                transformation_rule="rule",
                priority=-1,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("priority",) for e in errors)

        # Above maximum
        with pytest.raises(ValidationError) as exc_info:
            ConcreteTransformation(
                version=DEFAULT_VERSION,
                name="test-name",
                transformation_rule="rule",
                priority=1001,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("priority",) for e in errors)

    def test_case_sensitive_boolean(self):
        """Test case_sensitive accepts boolean values."""
        transform_true = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="rule",
            case_sensitive=True,
        )
        assert transform_true.case_sensitive is True

        transform_false = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="rule",
            case_sensitive=False,
        )
        assert transform_false.case_sensitive is False

    def test_apply_condition_optional(self):
        """Test apply_condition is optional."""
        transform = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="rule",
            apply_condition=None,
        )
        assert transform.apply_condition is None

        transform_with_condition = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="rule",
            apply_condition="condition",
        )
        assert transform_with_condition.apply_condition == "condition"


class TestBaseHeaderTransformationEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_minimum_priority(self):
        """Test transformation with minimum priority."""
        transform = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="low-priority",
            transformation_rule="rule",
            priority=0,
        )

        assert transform.priority == 0

    def test_maximum_priority(self):
        """Test transformation with maximum priority."""
        transform = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="high-priority",
            transformation_rule="rule",
            priority=1000,
        )

        assert transform.priority == 1000

    def test_template_transformation_rule(self):
        """Test transformation rule with template variables."""
        transform = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="Bearer {token}",
        )

        assert "{token}" in transform.transformation_rule

    def test_complex_apply_condition(self):
        """Test complex apply condition."""
        condition = "(request.path == '/api' and request.method == 'POST')"
        transform = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="rule",
            apply_condition=condition,
        )

        assert transform.apply_condition == condition

    def test_case_insensitive_matching(self):
        """Test case-insensitive matching configuration."""
        transform = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="rule",
            case_sensitive=False,
        )

        assert transform.case_sensitive is False


class TestBaseHeaderTransformationConfigDict:
    """Test ConfigDict behavior."""

    def test_extra_fields_ignored(self):
        """Test extra fields are ignored per ConfigDict."""
        transform = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="rule",
            unknown_field="should_be_ignored",  # type: ignore[call-arg]
        )

        assert transform.name == "test-name"
        assert not hasattr(transform, "unknown_field")

    def test_validate_assignment(self):
        """Test assignment validation is enabled."""
        transform = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="rule",
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
        original = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="Bearer {token}",
            apply_condition="request.path.startswith('/secure')",
            case_sensitive=False,
            priority=750,
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize
        restored = ConcreteTransformation(**data)

        assert restored.name == original.name
        assert restored.transformation_rule == original.transformation_rule
        assert restored.apply_condition == original.apply_condition
        assert restored.case_sensitive == original.case_sensitive
        assert restored.priority == original.priority

    def test_json_serialization(self):
        """Test model can be serialized to JSON."""
        transform = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="test-rule",
        )

        json_str = transform.model_dump_json()
        assert "test-name" in json_str
        assert "test-rule" in json_str


class TestBaseHeaderTransformationInheritance:
    """Test inheritance behavior."""

    def test_subclass_inherits_fields(self):
        """Test subclass properly inherits base class fields."""
        transform = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="rule",
        )

        # Check inherited fields exist
        assert hasattr(transform, "transformation_rule")
        assert hasattr(transform, "apply_condition")
        assert hasattr(transform, "case_sensitive")
        assert hasattr(transform, "priority")

    def test_subclass_can_override_defaults(self):
        """Test subclass can override base class defaults."""
        transform = ConcreteTransformation(
            version=DEFAULT_VERSION,
            name="test-name",
            transformation_rule="rule",
            priority=999,
        )

        assert transform.priority == 999

    def test_subclass_validation_applies(self):
        """Test base class validation applies to subclass."""
        # Priority out of bounds should fail
        with pytest.raises(ValidationError):
            ConcreteTransformation(
                version=DEFAULT_VERSION,
                name="test-name",
                transformation_rule="rule",
                priority=2000,
            )

        # Empty transformation_rule should fail
        with pytest.raises(ValidationError):
            ConcreteTransformation(
                version=DEFAULT_VERSION,
                name="test-name",
                transformation_rule="",
            )


class TestBaseHeaderTransformationDocumentation:
    """Test documentation and interface guarantees."""

    def test_docstring_present(self):
        """Test base class has comprehensive docstring."""
        assert ModelBaseHeaderTransformation.__doc__ is not None
        assert len(ModelBaseHeaderTransformation.__doc__) > 50

    def test_field_descriptions(self):
        """Test all base class fields have descriptions."""
        # Get schema from concrete subclass
        schema = ConcreteTransformation.model_json_schema()

        # Check base class fields have descriptions
        base_fields = [
            "transformation_rule",
            "apply_condition",
            "case_sensitive",
            "priority",
        ]
        for field_name in base_fields:
            assert field_name in schema.get("properties", {}), (
                f"Field {field_name} not in schema"
            )
            field_info = schema["properties"][field_name]
            assert "description" in field_info, (
                f"Field {field_name} missing description"
            )
