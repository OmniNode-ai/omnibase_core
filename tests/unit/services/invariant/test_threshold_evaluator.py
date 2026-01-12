# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for threshold invariant evaluation."""

import pytest

from omnibase_core.enums import EnumInvariantType
from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.invariant import ModelInvariant
from omnibase_core.services.invariant.service_invariant_evaluator import (
    ServiceInvariantEvaluator,
)


@pytest.mark.unit
class TestThresholdEvaluator:
    """Test suite for threshold invariant type."""

    def test_threshold_within_bounds_passes(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Value within min/max passes."""
        invariant = ModelInvariant(
            name="Confidence Check",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumSeverity.CRITICAL,
            config={
                "metric_name": "confidence",
                "min_value": 0.7,
                "max_value": 1.0,
            },
        )

        result = evaluator.evaluate(invariant, {"confidence": 0.85})
        assert result.passed is True

    def test_threshold_below_min_fails(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Value below min fails with clear message."""
        invariant = ModelInvariant(
            name="Confidence Check",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumSeverity.CRITICAL,
            config={
                "metric_name": "confidence",
                "min_value": 0.7,
                "max_value": 1.0,
            },
        )

        result = evaluator.evaluate(invariant, {"confidence": 0.5})

        assert result.passed is False
        assert result.actual_value == 0.5
        assert "0.5" in result.message or "below minimum" in result.message.lower()

    def test_threshold_above_max_fails(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Value above max fails with clear message."""
        invariant = ModelInvariant(
            name="Token Limit",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumSeverity.WARNING,
            config={
                "metric_name": "token_count",
                "min_value": 0,
                "max_value": 1000,
            },
        )

        result = evaluator.evaluate(invariant, {"token_count": 1500})

        assert result.passed is False
        assert result.actual_value == 1500
        assert "above maximum" in result.message.lower() or "1500" in result.message

    def test_threshold_min_only(self, evaluator: ServiceInvariantEvaluator) -> None:
        """Only min bound specified works."""
        invariant = ModelInvariant(
            name="Min Score",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumSeverity.CRITICAL,
            config={
                "metric_name": "score",
                "min_value": 0.5,
            },
        )

        # Above min
        result = evaluator.evaluate(invariant, {"score": 0.9})
        assert result.passed is True

        # Below min
        result = evaluator.evaluate(invariant, {"score": 0.3})
        assert result.passed is False

    def test_threshold_max_only(self, evaluator: ServiceInvariantEvaluator) -> None:
        """Only max bound specified works."""
        invariant = ModelInvariant(
            name="Max Tokens",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumSeverity.WARNING,
            config={
                "metric_name": "tokens",
                "max_value": 100,
            },
        )

        # Below max
        result = evaluator.evaluate(invariant, {"tokens": 50})
        assert result.passed is True

        # Above max
        result = evaluator.evaluate(invariant, {"tokens": 150})
        assert result.passed is False

    def test_threshold_at_boundary_passes(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Values exactly at min/max boundaries pass."""
        invariant = ModelInvariant(
            name="Boundary Check",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumSeverity.CRITICAL,
            config={
                "metric_name": "value",
                "min_value": 0.0,
                "max_value": 1.0,
            },
        )

        # Exactly at min
        result = evaluator.evaluate(invariant, {"value": 0.0})
        assert result.passed is True

        # Exactly at max
        result = evaluator.evaluate(invariant, {"value": 1.0})
        assert result.passed is True

    def test_threshold_metric_not_found_fails(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Missing metric field fails with clear message."""
        invariant = ModelInvariant(
            name="Missing Metric",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumSeverity.CRITICAL,
            config={
                "metric_name": "nonexistent",
                "min_value": 0.5,
            },
        )

        result = evaluator.evaluate(invariant, {"other_field": 0.8})

        assert result.passed is False
        assert "not found" in result.message.lower()

    def test_threshold_non_numeric_value_fails(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Non-numeric metric value fails gracefully."""
        invariant = ModelInvariant(
            name="Numeric Check",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumSeverity.CRITICAL,
            config={
                "metric_name": "value",
                "min_value": 0.5,
            },
        )

        result = evaluator.evaluate(invariant, {"value": "not a number"})

        assert result.passed is False
        assert "not numeric" in result.message.lower()

    def test_threshold_nested_metric_path(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Nested metric path (dot notation) works."""
        invariant = ModelInvariant(
            name="Nested Metric",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumSeverity.WARNING,
            config={
                "metric_name": "metrics.accuracy",
                "min_value": 0.9,
            },
        )

        result = evaluator.evaluate(invariant, {"metrics": {"accuracy": 0.95}})
        assert result.passed is True

        result = evaluator.evaluate(invariant, {"metrics": {"accuracy": 0.85}})
        assert result.passed is False

    def test_threshold_integer_values(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Integer metric values work correctly."""
        invariant = ModelInvariant(
            name="Integer Check",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumSeverity.CRITICAL,
            config={
                "metric_name": "count",
                "min_value": 10,
                "max_value": 100,
            },
        )

        result = evaluator.evaluate(invariant, {"count": 50})
        assert result.passed is True

        result = evaluator.evaluate(invariant, {"count": 5})
        assert result.passed is False

    def test_threshold_negative_values(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Negative threshold values work correctly."""
        invariant = ModelInvariant(
            name="Temperature Check",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumSeverity.WARNING,
            config={
                "metric_name": "temperature",
                "min_value": -10.0,
                "max_value": 10.0,
            },
        )

        result = evaluator.evaluate(invariant, {"temperature": -5.0})
        assert result.passed is True

        result = evaluator.evaluate(invariant, {"temperature": -15.0})
        assert result.passed is False
