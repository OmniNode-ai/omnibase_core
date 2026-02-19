# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for schema validation invariant evaluation."""

import pytest

from omnibase_core.enums import EnumInvariantType, EnumSeverity
from omnibase_core.models.invariant import ModelInvariant
from omnibase_core.services.invariant.service_invariant_evaluator import (
    ServiceInvariantEvaluator,
)


@pytest.mark.unit
class TestSchemaEvaluator:
    """Test suite for schema validation invariant type."""

    def test_schema_passes_valid_output(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Valid output passes schema validation."""
        invariant = ModelInvariant(
            name="Valid Schema",
            type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.CRITICAL,
            config={
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "count": {"type": "integer"},
                    },
                    "required": ["status"],
                }
            },
        )
        output = {"status": "success", "count": 42}

        result = evaluator.evaluate(invariant, output)

        assert result.passed is True
        assert result.invariant_name == "Valid Schema"

    def test_schema_fails_missing_required_field(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Missing required field fails with clear message."""
        invariant = ModelInvariant(
            name="Required Field Check",
            type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.CRITICAL,
            config={
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                    },
                    "required": ["name", "email"],
                }
            },
        )
        output = {"name": "Alice"}  # Missing email

        result = evaluator.evaluate(invariant, output)

        assert result.passed is False
        assert (
            "email" in result.message.lower()
            or "'email' is a required property" in result.message
        )

    def test_schema_fails_wrong_type(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Wrong type in field fails with path to error."""
        invariant = ModelInvariant(
            name="Type Check",
            type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.WARNING,
            config={
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "age": {"type": "integer"},
                    },
                }
            },
        )
        output = {"age": "not a number"}

        result = evaluator.evaluate(invariant, output)

        assert result.passed is False
        assert "age" in result.message.lower() or "integer" in result.message.lower()

    def test_schema_validates_nested_objects(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Nested object validation works correctly."""
        invariant = ModelInvariant(
            name="Nested Schema",
            type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.CRITICAL,
            config={
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "user": {
                            "type": "object",
                            "properties": {
                                "profile": {
                                    "type": "object",
                                    "properties": {
                                        "verified": {"type": "boolean"},
                                    },
                                    "required": ["verified"],
                                }
                            },
                            "required": ["profile"],
                        }
                    },
                    "required": ["user"],
                }
            },
        )

        # Valid nested structure
        valid_output = {"user": {"profile": {"verified": True}}}
        result = evaluator.evaluate(invariant, valid_output)
        assert result.passed is True

        # Invalid nested structure
        invalid_output = {"user": {"profile": {"verified": "yes"}}}  # Should be boolean
        result = evaluator.evaluate(invariant, invalid_output)
        assert result.passed is False

    def test_schema_validates_array_items(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Array item validation works correctly."""
        invariant = ModelInvariant(
            name="Array Schema",
            type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.CRITICAL,
            config={
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "integer"},
                                    "name": {"type": "string"},
                                },
                                "required": ["id"],
                            },
                        }
                    },
                    "required": ["items"],
                }
            },
        )

        # Valid array
        valid_output = {"items": [{"id": 1, "name": "foo"}, {"id": 2}]}
        result = evaluator.evaluate(invariant, valid_output)
        assert result.passed is True

        # Invalid array item
        invalid_output = {"items": [{"id": "not-an-int"}]}
        result = evaluator.evaluate(invariant, invalid_output)
        assert result.passed is False

    def test_schema_invalid_config_missing_json_schema(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Missing json_schema in config is caught by ModelInvariant validation."""
        from pydantic import ValidationError

        # ModelInvariant validates that SCHEMA type requires json_schema
        with pytest.raises(ValidationError) as exc_info:
            ModelInvariant(
                name="Invalid Config",
                type=EnumInvariantType.SCHEMA,
                severity=EnumSeverity.CRITICAL,
                config={},  # Missing json_schema
            )

        assert "json_schema" in str(exc_info.value).lower()

    def test_schema_invalid_config_non_dict_schema(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Non-dict json_schema in config returns appropriate error."""
        invariant = ModelInvariant(
            name="Invalid Config Type",
            type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.CRITICAL,
            config={"json_schema": "not a dict"},
        )
        output = {"any": "data"}

        result = evaluator.evaluate(invariant, output)

        assert result.passed is False
        assert "must be a dict" in result.message

    def test_schema_additional_properties_validation(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Additional properties constraint is enforced."""
        invariant = ModelInvariant(
            name="No Additional Properties",
            type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.WARNING,
            config={
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "allowed": {"type": "string"},
                    },
                    "additionalProperties": False,
                }
            },
        )

        # Valid - only allowed property
        valid_output = {"allowed": "value"}
        result = evaluator.evaluate(invariant, valid_output)
        assert result.passed is True

        # Invalid - extra property
        invalid_output = {"allowed": "value", "extra": "not allowed"}
        result = evaluator.evaluate(invariant, invalid_output)
        assert result.passed is False

    def test_schema_pattern_validation(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """String pattern validation works correctly."""
        invariant = ModelInvariant(
            name="Email Pattern",
            type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.CRITICAL,
            config={
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "pattern": "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$",
                        },
                    },
                }
            },
        )

        # Valid email pattern
        valid_output = {"email": "test@example.com"}
        result = evaluator.evaluate(invariant, valid_output)
        assert result.passed is True

        # Invalid email pattern
        invalid_output = {"email": "not-an-email"}
        result = evaluator.evaluate(invariant, invalid_output)
        assert result.passed is False

    def test_schema_enum_validation(self, evaluator: ServiceInvariantEvaluator) -> None:
        """Enum constraint validation works correctly."""
        invariant = ModelInvariant(
            name="Status Enum",
            type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.CRITICAL,
            config={
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["pending", "active", "completed"],
                        },
                    },
                }
            },
        )

        # Valid enum value
        valid_output = {"status": "active"}
        result = evaluator.evaluate(invariant, valid_output)
        assert result.passed is True

        # Invalid enum value
        invalid_output = {"status": "unknown"}
        result = evaluator.evaluate(invariant, invalid_output)
        assert result.passed is False

    def test_schema_minimum_maximum_validation(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Numeric min/max constraints are validated."""
        invariant = ModelInvariant(
            name="Age Range",
            type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.WARNING,
            config={
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "age": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 150,
                        },
                    },
                }
            },
        )

        # Valid age
        valid_output = {"age": 25}
        result = evaluator.evaluate(invariant, valid_output)
        assert result.passed is True

        # Age below minimum
        below_min_output = {"age": -1}
        result = evaluator.evaluate(invariant, below_min_output)
        assert result.passed is False

        # Age above maximum
        above_max_output = {"age": 200}
        result = evaluator.evaluate(invariant, above_max_output)
        assert result.passed is False

    def test_schema_result_contains_severity(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Result contains correct severity from invariant."""
        for severity in [
            EnumSeverity.CRITICAL,
            EnumSeverity.WARNING,
            EnumSeverity.INFO,
        ]:
            invariant = ModelInvariant(
                name=f"Severity Test {severity.value}",
                type=EnumInvariantType.SCHEMA,
                severity=severity,
                config={
                    "json_schema": {
                        "type": "object",
                    }
                },
            )
            result = evaluator.evaluate(invariant, {})
            assert result.severity == severity

    def test_schema_result_contains_invariant_id(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Result contains invariant_id from the invariant."""
        invariant = ModelInvariant(
            name="ID Test",
            type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.INFO,
            config={
                "json_schema": {"type": "object"},
            },
        )
        result = evaluator.evaluate(invariant, {})
        assert result.invariant_id == invariant.id

    def test_schema_result_contains_evaluated_at_timestamp(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Result contains evaluated_at timestamp."""
        invariant = ModelInvariant(
            name="Timestamp Test",
            type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.INFO,
            config={
                "json_schema": {"type": "object"},
            },
        )
        result = evaluator.evaluate(invariant, {})
        assert result.evaluated_at is not None
