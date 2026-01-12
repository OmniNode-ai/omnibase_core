# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for latency invariant evaluation."""

import pytest

from omnibase_core.enums import EnumInvariantType
from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.invariant import ModelInvariant
from omnibase_core.services.invariant.service_invariant_evaluator import (
    ServiceInvariantEvaluator,
)


@pytest.mark.unit
class TestLatencyEvaluator:
    """Test suite for latency invariant type."""

    def test_latency_under_limit_passes(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Latency under max_ms passes."""
        invariant = ModelInvariant(
            name="Response Time",
            type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            config={"max_ms": 5000},
        )

        result = evaluator.evaluate(invariant, {"latency_ms": 1200})
        assert result.passed is True
        assert result.actual_value == 1200
        assert result.expected_value == 5000

    def test_latency_over_limit_fails(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Latency over max_ms fails with actual vs limit."""
        invariant = ModelInvariant(
            name="Response Time",
            type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.CRITICAL,
            config={"max_ms": 2000},
        )

        result = evaluator.evaluate(invariant, {"latency_ms": 3500})

        assert result.passed is False
        assert result.actual_value == 3500
        assert result.expected_value == 2000
        assert "3500" in result.message or "exceeds" in result.message.lower()

    def test_latency_supports_duration_ms_field(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Alternative field name duration_ms works."""
        invariant = ModelInvariant(
            name="Duration Check",
            type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            config={"max_ms": 1000},
        )

        # Using duration_ms instead of latency_ms
        result = evaluator.evaluate(invariant, {"duration_ms": 500})
        assert result.passed is True
        assert result.actual_value == 500

    def test_latency_at_exact_limit_passes(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Latency exactly at max_ms passes (<=)."""
        invariant = ModelInvariant(
            name="Exact Limit",
            type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.CRITICAL,
            config={"max_ms": 1000},
        )

        result = evaluator.evaluate(invariant, {"latency_ms": 1000})
        assert result.passed is True

    def test_latency_zero_passes(self, evaluator: ServiceInvariantEvaluator) -> None:
        """Zero latency passes."""
        invariant = ModelInvariant(
            name="Zero Latency",
            type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            config={"max_ms": 1000},
        )

        result = evaluator.evaluate(invariant, {"latency_ms": 0})
        assert result.passed is True

    def test_latency_missing_field_fails(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Missing latency_ms and duration_ms fails with clear message."""
        invariant = ModelInvariant(
            name="Missing Latency",
            type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.CRITICAL,
            config={"max_ms": 1000},
        )

        result = evaluator.evaluate(invariant, {"other_field": 500})

        assert result.passed is False
        assert "not found" in result.message.lower()

    def test_latency_prefers_latency_ms_over_duration_ms(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """When both fields present, latency_ms is preferred."""
        invariant = ModelInvariant(
            name="Preference Check",
            type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            config={"max_ms": 1000},
        )

        # Both fields present - latency_ms should be used
        result = evaluator.evaluate(invariant, {"latency_ms": 500, "duration_ms": 2000})
        assert result.passed is True
        assert result.actual_value == 500

    def test_latency_float_values(self, evaluator: ServiceInvariantEvaluator) -> None:
        """Float latency values work correctly."""
        invariant = ModelInvariant(
            name="Float Latency",
            type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            config={"max_ms": 100.5},
        )

        result = evaluator.evaluate(invariant, {"latency_ms": 100.0})
        assert result.passed is True

        result = evaluator.evaluate(invariant, {"latency_ms": 101.0})
        assert result.passed is False

    def test_latency_non_numeric_value_fails(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Non-numeric latency value fails gracefully."""
        invariant = ModelInvariant(
            name="Non-Numeric",
            type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.CRITICAL,
            config={"max_ms": 1000},
        )

        result = evaluator.evaluate(invariant, {"latency_ms": "fast"})

        assert result.passed is False
        assert "not found" in result.message.lower() or result.actual_value is None

    def test_latency_very_large_value(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Very large latency values handled correctly."""
        invariant = ModelInvariant(
            name="Large Latency",
            type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            config={"max_ms": 60000},  # 60 seconds
        )

        result = evaluator.evaluate(invariant, {"latency_ms": 300000})  # 5 minutes
        assert result.passed is False
        assert result.actual_value == 300000

    def test_latency_message_contains_both_values(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Failure message contains both actual and expected values."""
        invariant = ModelInvariant(
            name="Message Check",
            type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.CRITICAL,
            config={"max_ms": 500},
        )

        result = evaluator.evaluate(invariant, {"latency_ms": 750})

        assert result.passed is False
        # Message should contain actual and limit
        assert "750" in result.message
        assert "500" in result.message
