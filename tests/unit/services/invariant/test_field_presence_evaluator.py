# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for field presence invariant evaluation."""

from typing import Any

import pytest

from omnibase_core.enums import EnumInvariantType, EnumSeverity
from omnibase_core.models.invariant import ModelInvariant
from omnibase_core.services.invariant.service_invariant_evaluator import (
    ServiceInvariantEvaluator,
)


@pytest.mark.unit
class TestFieldPresenceEvaluator:
    """Test suite for field presence invariant type."""

    def test_field_presence_passes_all_present(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """All required fields present passes."""
        invariant = ModelInvariant(
            name="Required Fields",
            type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumSeverity.CRITICAL,
            config={"fields": ["name", "email", "id"]},
        )
        output = {"name": "Alice", "email": "alice@example.com", "id": 123}

        result = evaluator.evaluate(invariant, output)

        assert result.passed is True

    def test_field_presence_fails_missing_field(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Missing field fails with field name in message."""
        invariant = ModelInvariant(
            name="Required Fields",
            type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumSeverity.CRITICAL,
            config={"fields": ["name", "email", "phone"]},
        )
        output = {"name": "Alice", "email": "alice@example.com"}

        result = evaluator.evaluate(invariant, output)

        assert result.passed is False
        assert "phone" in result.message

    def test_field_presence_supports_nested_paths(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Dot notation paths like 'a.b.c' work."""
        invariant = ModelInvariant(
            name="Nested Fields",
            type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumSeverity.WARNING,
            config={"fields": ["user.profile.email", "user.settings.theme"]},
        )

        # All present
        output = {
            "user": {
                "profile": {"email": "test@example.com"},
                "settings": {"theme": "dark"},
            }
        }
        result = evaluator.evaluate(invariant, output)
        assert result.passed is True

        # Missing nested field
        output_missing = {
            "user": {
                "profile": {"email": "test@example.com"},
                "settings": {},  # Missing theme
            }
        }
        result = evaluator.evaluate(invariant, output_missing)
        assert result.passed is False
        assert "theme" in result.message or "settings.theme" in result.message

    def test_field_presence_supports_array_indices(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Array indices like 'items.0.id' work."""
        invariant = ModelInvariant(
            name="Array Fields",
            type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumSeverity.CRITICAL,
            config={"fields": ["items.0.id", "items.0.name"]},
        )

        # Valid array access
        output = {"items": [{"id": 1, "name": "First"}]}
        result = evaluator.evaluate(invariant, output)
        assert result.passed is True

        # Missing field in array element
        output_missing = {"items": [{"id": 1}]}  # Missing name
        result = evaluator.evaluate(invariant, output_missing)
        assert result.passed is False

    def test_field_presence_empty_fields_list_passes(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Empty fields list always passes."""
        invariant = ModelInvariant(
            name="No Required Fields",
            type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumSeverity.WARNING,
            config={"fields": []},
        )
        output = {"any": "data"}

        result = evaluator.evaluate(invariant, output)

        assert result.passed is True

    def test_field_presence_handles_none_values(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Field with None value counts as present."""
        invariant = ModelInvariant(
            name="Nullable Fields",
            type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumSeverity.CRITICAL,
            config={"fields": ["name", "optional_field"]},
        )
        output = {"name": "Alice", "optional_field": None}

        result = evaluator.evaluate(invariant, output)

        assert result.passed is True

    def test_field_presence_handles_empty_output(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Empty output fails when fields are required."""
        invariant = ModelInvariant(
            name="Required Fields",
            type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumSeverity.CRITICAL,
            config={"fields": ["name"]},
        )
        output: dict[str, object] = {}

        result = evaluator.evaluate(invariant, output)

        assert result.passed is False
        assert "name" in result.message

    def test_field_presence_multiple_missing_fields(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Multiple missing fields are all reported."""
        invariant = ModelInvariant(
            name="Multiple Required",
            type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumSeverity.CRITICAL,
            config={"fields": ["field_a", "field_b", "field_c"]},
        )
        output = {"field_a": "present"}

        result = evaluator.evaluate(invariant, output)

        assert result.passed is False
        assert "field_b" in result.message
        assert "field_c" in result.message

    def test_field_presence_deeply_nested_path(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Deeply nested paths work correctly."""
        invariant = ModelInvariant(
            name="Deep Nested",
            type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumSeverity.WARNING,
            config={"fields": ["level1.level2.level3.level4.value"]},
        )

        output = {"level1": {"level2": {"level3": {"level4": {"value": "deep"}}}}}
        result = evaluator.evaluate(invariant, output)
        assert result.passed is True

        # Missing intermediate level
        output_broken: dict[str, Any] = {"level1": {"level2": {"level3": {}}}}
        result = evaluator.evaluate(invariant, output_broken)
        assert result.passed is False

    def test_field_presence_array_out_of_bounds(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Array index out of bounds fails gracefully."""
        invariant = ModelInvariant(
            name="Array Bounds",
            type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumSeverity.CRITICAL,
            config={"fields": ["items.5.id"]},
        )
        output = {"items": [{"id": 1}, {"id": 2}]}

        result = evaluator.evaluate(invariant, output)

        assert result.passed is False
        assert "items.5.id" in result.message

    def test_field_presence_mixed_array_and_dict_path(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Mixed array and dict paths work."""
        invariant = ModelInvariant(
            name="Mixed Path",
            type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumSeverity.CRITICAL,
            config={"fields": ["users.0.addresses.1.city"]},
        )

        output = {
            "users": [
                {
                    "name": "Alice",
                    "addresses": [
                        {"city": "NYC"},
                        {"city": "LA"},
                    ],
                }
            ]
        }
        result = evaluator.evaluate(invariant, output)
        assert result.passed is True

    def test_field_presence_result_contains_expected_fields(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Result includes expected_value with required fields list."""
        invariant = ModelInvariant(
            name="Check Expected",
            type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumSeverity.WARNING,
            config={"fields": ["a", "b", "c"]},
        )
        output = {"a": 1, "b": 2, "c": 3}

        result = evaluator.evaluate(invariant, output)

        assert result.passed is True
        assert result.expected_value == ["a", "b", "c"]
