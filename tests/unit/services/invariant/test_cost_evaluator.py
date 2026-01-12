# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for cost invariant evaluation."""

import pytest

from omnibase_core.enums import EnumInvariantType
from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.invariant import ModelInvariant
from omnibase_core.services.invariant.service_invariant_evaluator import (
    ServiceInvariantEvaluator,
)


@pytest.mark.unit
class TestCostEvaluator:
    """Test suite for cost invariant type."""

    def test_cost_under_budget_passes(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Cost under max_cost passes."""
        invariant = ModelInvariant(
            name="Request Cost",
            type=EnumInvariantType.COST,
            severity=EnumSeverity.CRITICAL,
            config={"max_cost": 0.10, "per": "request"},
        )

        result = evaluator.evaluate(invariant, {"cost": 0.05})
        assert result.passed is True
        assert result.actual_value == 0.05

    def test_cost_over_budget_fails(self, evaluator: ServiceInvariantEvaluator) -> None:
        """Cost over max_cost fails."""
        invariant = ModelInvariant(
            name="Request Cost",
            type=EnumInvariantType.COST,
            severity=EnumSeverity.CRITICAL,
            config={"max_cost": 0.10, "per": "request"},
        )

        result = evaluator.evaluate(invariant, {"cost": 0.25})

        assert result.passed is False
        assert result.actual_value == 0.25
        assert "exceeds" in result.message.lower() or "0.25" in result.message

    def test_cost_calculates_from_tokens(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Cost calculated from token usage if not provided directly."""
        invariant = ModelInvariant(
            name="Token Cost",
            type=EnumInvariantType.COST,
            severity=EnumSeverity.WARNING,
            config={"max_cost": 0.10, "per": "request"},
        )

        # If cost field not present, should try to calculate from usage.total_tokens
        # Default rate: $0.0001 per token (from implementation)
        output = {"usage": {"total_tokens": 500}}
        result = evaluator.evaluate(invariant, output)

        # 500 tokens * 0.0001 = 0.05, which is under 0.10
        assert result is not None
        assert result.invariant_name == "Token Cost"
        assert result.passed is True
        assert result.actual_value == 0.05

    def test_cost_token_calculation_exceeds_budget(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Token-calculated cost exceeding budget fails."""
        invariant = ModelInvariant(
            name="Token Cost Exceeded",
            type=EnumInvariantType.COST,
            severity=EnumSeverity.CRITICAL,
            config={"max_cost": 0.05, "per": "request"},
        )

        # 1000 tokens * 0.0001 = 0.10, which exceeds 0.05
        output = {"usage": {"total_tokens": 1000}}
        result = evaluator.evaluate(invariant, output)

        assert result.passed is False
        assert result.actual_value == 0.10

    def test_cost_custom_token_rate(self, evaluator: ServiceInvariantEvaluator) -> None:
        """Custom cost_per_token rate is used when specified."""
        invariant = ModelInvariant(
            name="Custom Rate",
            type=EnumInvariantType.COST,
            severity=EnumSeverity.WARNING,
            config={"max_cost": 0.10, "cost_per_token": 0.001},
        )

        # 50 tokens * 0.001 = 0.05, under budget
        output = {"usage": {"total_tokens": 50}}
        result = evaluator.evaluate(invariant, output)

        assert result.passed is True
        assert result.actual_value == 0.05

    def test_cost_at_exact_budget_passes(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Cost exactly at max_cost passes (<=)."""
        invariant = ModelInvariant(
            name="Exact Budget",
            type=EnumInvariantType.COST,
            severity=EnumSeverity.CRITICAL,
            config={"max_cost": 0.10},
        )

        result = evaluator.evaluate(invariant, {"cost": 0.10})
        assert result.passed is True

    def test_cost_zero_passes(self, evaluator: ServiceInvariantEvaluator) -> None:
        """Zero cost passes."""
        invariant = ModelInvariant(
            name="Zero Cost",
            type=EnumInvariantType.COST,
            severity=EnumSeverity.WARNING,
            config={"max_cost": 0.10},
        )

        result = evaluator.evaluate(invariant, {"cost": 0.0})
        assert result.passed is True

    def test_cost_missing_field_fails(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Missing cost and usage.total_tokens fails with clear message."""
        invariant = ModelInvariant(
            name="Missing Cost",
            type=EnumInvariantType.COST,
            severity=EnumSeverity.CRITICAL,
            config={"max_cost": 0.10},
        )

        result = evaluator.evaluate(invariant, {"other_field": 0.05})

        assert result.passed is False
        assert "not found" in result.message.lower()

    def test_cost_direct_field_preferred_over_tokens(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Direct cost field is preferred over token calculation."""
        invariant = ModelInvariant(
            name="Preference Check",
            type=EnumInvariantType.COST,
            severity=EnumSeverity.WARNING,
            config={"max_cost": 0.10},
        )

        # Both cost and usage.total_tokens present - cost should be used
        result = evaluator.evaluate(
            invariant, {"cost": 0.03, "usage": {"total_tokens": 10000}}
        )
        assert result.passed is True
        assert result.actual_value == 0.03

    def test_cost_very_small_values(self, evaluator: ServiceInvariantEvaluator) -> None:
        """Very small cost values handled correctly."""
        invariant = ModelInvariant(
            name="Small Cost",
            type=EnumInvariantType.COST,
            severity=EnumSeverity.WARNING,
            config={"max_cost": 0.001},
        )

        result = evaluator.evaluate(invariant, {"cost": 0.0005})
        assert result.passed is True
        assert result.actual_value == 0.0005

    def test_cost_large_budget(self, evaluator: ServiceInvariantEvaluator) -> None:
        """Large budget values handled correctly."""
        invariant = ModelInvariant(
            name="Large Budget",
            type=EnumInvariantType.COST,
            severity=EnumSeverity.CRITICAL,
            config={"max_cost": 100.0},
        )

        result = evaluator.evaluate(invariant, {"cost": 50.0})
        assert result.passed is True

        result = evaluator.evaluate(invariant, {"cost": 150.0})
        assert result.passed is False

    def test_cost_non_numeric_value_fails(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Non-numeric cost value fails gracefully."""
        invariant = ModelInvariant(
            name="Non-Numeric",
            type=EnumInvariantType.COST,
            severity=EnumSeverity.CRITICAL,
            config={"max_cost": 0.10},
        )

        result = evaluator.evaluate(invariant, {"cost": "expensive"})

        assert result.passed is False
        assert "invalid" in result.message.lower()

    def test_cost_message_contains_values(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Failure message contains both actual and expected values."""
        invariant = ModelInvariant(
            name="Message Check",
            type=EnumInvariantType.COST,
            severity=EnumSeverity.CRITICAL,
            config={"max_cost": 0.05},
        )

        result = evaluator.evaluate(invariant, {"cost": 0.15})

        assert result.passed is False
        # Message should contain actual and limit
        assert "0.15" in result.message
        assert "0.05" in result.message

    def test_cost_integer_tokens(self, evaluator: ServiceInvariantEvaluator) -> None:
        """Integer token counts work correctly."""
        invariant = ModelInvariant(
            name="Integer Tokens",
            type=EnumInvariantType.COST,
            severity=EnumSeverity.WARNING,
            config={"max_cost": 1.0},
        )

        # 5000 tokens * 0.0001 = 0.5, under budget
        result = evaluator.evaluate(invariant, {"usage": {"total_tokens": 5000}})
        assert result.passed is True
        assert result.actual_value == 0.5

    def test_cost_severity_preserved(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Result preserves the severity from the invariant."""
        invariant = ModelInvariant(
            name="Severity Check",
            type=EnumInvariantType.COST,
            severity=EnumSeverity.INFO,
            config={"max_cost": 0.01},
        )

        result = evaluator.evaluate(invariant, {"cost": 0.50})

        assert result.passed is False
        assert result.severity == EnumSeverity.INFO
