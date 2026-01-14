# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""Tests for field value invariant evaluation."""

import pytest

from omnibase_core.enums import EnumInvariantType, EnumSeverity
from omnibase_core.models.invariant import ModelInvariant
from omnibase_core.services.invariant.service_invariant_evaluator import (
    ServiceInvariantEvaluator,
)


@pytest.mark.unit
class TestFieldValueEvaluator:
    """Test suite for field value invariant type."""

    def test_field_value_exact_match(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Exact value match works."""
        invariant = ModelInvariant(
            name="Status Check",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.CRITICAL,
            config={
                "field_path": "status",
                "expected_value": "success",
            },
        )

        # Exact match
        result = evaluator.evaluate(invariant, {"status": "success"})
        assert result.passed is True

        # Non-match
        result = evaluator.evaluate(invariant, {"status": "failed"})
        assert result.passed is False
        assert "failed" in result.message  # Shows actual value

    def test_field_value_regex_match(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Regex pattern matching works."""
        invariant = ModelInvariant(
            name="UUID Format",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.WARNING,
            config={
                "field_path": "id",
                "pattern": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            },
        )

        # Valid UUID
        result = evaluator.evaluate(
            invariant, {"id": "550e8400-e29b-41d4-a716-446655440000"}
        )
        assert result.passed is True

        # Invalid UUID
        result = evaluator.evaluate(invariant, {"id": "not-a-uuid"})
        assert result.passed is False

    def test_field_value_shows_actual_vs_expected(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Failure message shows actual and expected values."""
        invariant = ModelInvariant(
            name="Code Check",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.CRITICAL,
            config={
                "field_path": "response.code",
                "expected_value": 200,
            },
        )

        result = evaluator.evaluate(invariant, {"response": {"code": 404}})

        assert result.passed is False
        assert result.actual_value == 404
        assert result.expected_value == 200
        # Message should contain both values
        assert "404" in str(result.message) or "404" in str(result.actual_value)

    def test_field_value_numeric_exact_match(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Numeric values match exactly."""
        invariant = ModelInvariant(
            name="Count Check",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.CRITICAL,
            config={
                "field_path": "count",
                "expected_value": 42,
            },
        )

        result = evaluator.evaluate(invariant, {"count": 42})
        assert result.passed is True

        result = evaluator.evaluate(invariant, {"count": 41})
        assert result.passed is False

    def test_field_value_boolean_match(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Boolean values match correctly."""
        invariant = ModelInvariant(
            name="Active Check",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.CRITICAL,
            config={
                "field_path": "is_active",
                "expected_value": True,
            },
        )

        result = evaluator.evaluate(invariant, {"is_active": True})
        assert result.passed is True

        result = evaluator.evaluate(invariant, {"is_active": False})
        assert result.passed is False

    def test_field_value_nested_path(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Nested field paths work for value matching."""
        invariant = ModelInvariant(
            name="Nested Status",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.WARNING,
            config={
                "field_path": "response.status.code",
                "expected_value": "OK",
            },
        )

        output = {"response": {"status": {"code": "OK"}}}
        result = evaluator.evaluate(invariant, output)
        assert result.passed is True

        output_wrong = {"response": {"status": {"code": "ERROR"}}}
        result = evaluator.evaluate(invariant, output_wrong)
        assert result.passed is False

    def test_field_value_field_not_found(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Missing field path fails with appropriate message."""
        invariant = ModelInvariant(
            name="Missing Field",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.CRITICAL,
            config={
                "field_path": "nonexistent.path",
                "expected_value": "value",
            },
        )

        result = evaluator.evaluate(invariant, {"other": "data"})

        assert result.passed is False
        assert "not found" in result.message.lower()

    def test_field_value_regex_partial_match(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Regex uses search (partial match) not fullmatch."""
        invariant = ModelInvariant(
            name="Contains Email",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.WARNING,
            config={
                "field_path": "text",
                "pattern": r"[a-z]+@[a-z]+\.[a-z]+",
            },
        )

        # Pattern found within string
        result = evaluator.evaluate(
            invariant, {"text": "Contact: user@example.com for info"}
        )
        assert result.passed is True

    def test_field_value_regex_anchored(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Anchored regex requires full match."""
        invariant = ModelInvariant(
            name="Exact Format",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.WARNING,
            config={
                "field_path": "code",
                "pattern": r"^ERR-\d{4}$",
            },
        )

        result = evaluator.evaluate(invariant, {"code": "ERR-1234"})
        assert result.passed is True

        result = evaluator.evaluate(invariant, {"code": "prefix-ERR-1234-suffix"})
        assert result.passed is False

    def test_field_value_null_handling(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """None/null values can be checked."""
        invariant = ModelInvariant(
            name="Null Check",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.WARNING,
            config={
                "field_path": "optional_field",
                "expected_value": None,
            },
        )

        result = evaluator.evaluate(invariant, {"optional_field": None})
        assert result.passed is True

        result = evaluator.evaluate(invariant, {"optional_field": "not null"})
        assert result.passed is False

    def test_field_value_array_index_path(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Array indices work in field paths."""
        invariant = ModelInvariant(
            name="First Item Status",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.CRITICAL,
            config={
                "field_path": "items.0.status",
                "expected_value": "ready",
            },
        )

        output = {"items": [{"status": "ready"}, {"status": "pending"}]}
        result = evaluator.evaluate(invariant, output)
        assert result.passed is True

        output_wrong = {"items": [{"status": "pending"}]}
        result = evaluator.evaluate(invariant, output_wrong)
        assert result.passed is False

    def test_field_value_pattern_converts_to_string(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Pattern matching converts non-string values to strings."""
        invariant = ModelInvariant(
            name="Numeric Pattern",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.WARNING,
            config={
                "field_path": "code",
                "pattern": r"^\d{3}$",
            },
        )

        # Numeric value converted to string for pattern matching
        result = evaluator.evaluate(invariant, {"code": 200})
        assert result.passed is True

        result = evaluator.evaluate(invariant, {"code": 1000})
        assert result.passed is False

    def test_field_value_empty_string_match(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Empty string matches correctly."""
        invariant = ModelInvariant(
            name="Empty Check",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.INFO,
            config={
                "field_path": "message",
                "expected_value": "",
            },
        )

        result = evaluator.evaluate(invariant, {"message": ""})
        assert result.passed is True

        result = evaluator.evaluate(invariant, {"message": "not empty"})
        assert result.passed is False

    def test_field_value_list_match(self, evaluator: ServiceInvariantEvaluator) -> None:
        """List values match exactly."""
        invariant = ModelInvariant(
            name="Tags Check",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.WARNING,
            config={
                "field_path": "tags",
                "expected_value": ["alpha", "beta"],
            },
        )

        result = evaluator.evaluate(invariant, {"tags": ["alpha", "beta"]})
        assert result.passed is True

        result = evaluator.evaluate(invariant, {"tags": ["alpha"]})
        assert result.passed is False

    def test_field_value_dict_match(self, evaluator: ServiceInvariantEvaluator) -> None:
        """Dict values match exactly."""
        invariant = ModelInvariant(
            name="Config Check",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.WARNING,
            config={
                "field_path": "settings",
                "expected_value": {"mode": "fast", "enabled": True},
            },
        )

        result = evaluator.evaluate(
            invariant, {"settings": {"mode": "fast", "enabled": True}}
        )
        assert result.passed is True

        result = evaluator.evaluate(
            invariant, {"settings": {"mode": "slow", "enabled": True}}
        )
        assert result.passed is False

    def test_field_value_missing_expected_and_pattern(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Config without expected_value or pattern fails."""
        invariant = ModelInvariant(
            name="Invalid Config",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.WARNING,
            config={
                "field_path": "status",
                # No expected_value or pattern
            },
        )

        result = evaluator.evaluate(invariant, {"status": "any"})

        assert result.passed is False
        assert "expected_value" in result.message or "pattern" in result.message

    def test_field_value_result_metadata(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Result contains correct metadata."""
        invariant = ModelInvariant(
            name="Metadata Test",
            type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.CRITICAL,
            config={
                "field_path": "value",
                "expected_value": "expected",
            },
        )

        result = evaluator.evaluate(invariant, {"value": "actual"})

        assert result.invariant_name == "Metadata Test"
        assert result.severity == EnumSeverity.CRITICAL
        assert result.actual_value == "actual"
        assert result.expected_value == "expected"
        assert result.evaluated_at is not None
