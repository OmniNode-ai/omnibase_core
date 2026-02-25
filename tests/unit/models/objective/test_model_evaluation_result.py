# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelEvaluationResult.

Tests cover: model construction, consistency invariants (passed/failures/score_vector),
and immutability. Part of OMN-2537.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.objective.model_evaluation_result import ModelEvaluationResult
from omnibase_core.models.objective.model_score_vector import ModelScoreVector


def _zero() -> ModelScoreVector:
    """Helper: return the zero score vector."""
    return ModelScoreVector.zero()


def _passing_score() -> ModelScoreVector:
    """Helper: return a non-zero passing score vector."""
    return ModelScoreVector(
        correctness=1.0,
        safety=0.95,
        cost=0.8,
        latency=0.75,
        maintainability=0.9,
        human_time=0.85,
    )


@pytest.mark.unit
class TestModelEvaluationResultConstruction:
    """Test ModelEvaluationResult instantiation."""

    def test_create_passing_result(self) -> None:
        """Create a passing EvaluationResult with non-zero score and no failures."""
        result = ModelEvaluationResult(
            passed=True,
            score_vector=_passing_score(),
            failures=[],
            attribution_refs=["item-1", "item-2"],
        )
        assert result.passed is True
        assert result.failures == []
        assert len(result.attribution_refs) == 2

    def test_create_failing_result_with_zero_vector(self) -> None:
        """Create a failing EvaluationResult with zero score and gate failures."""
        result = ModelEvaluationResult(
            passed=False,
            score_vector=_zero(),
            failures=["gate-tests", "gate-security"],
            attribution_refs=[],
        )
        assert result.passed is False
        assert result.score_vector == _zero()
        assert "gate-tests" in result.failures


@pytest.mark.unit
class TestModelEvaluationResultInvariants:
    """Test consistency invariants between fields."""

    def test_passed_false_requires_zero_score_vector(self) -> None:
        """When passed=False, score_vector must be ModelScoreVector.zero()."""
        with pytest.raises(ValidationError):
            ModelEvaluationResult(
                passed=False,
                score_vector=_passing_score(),  # Non-zero: invalid when passed=False
                failures=["gate-tests"],
                attribution_refs=[],
            )

    def test_passed_true_requires_empty_failures(self) -> None:
        """When passed=True, failures must be empty."""
        with pytest.raises(ValidationError):
            ModelEvaluationResult(
                passed=True,
                score_vector=_passing_score(),
                failures=["gate-tests"],  # Non-empty: invalid when passed=True
                attribution_refs=[],
            )

    def test_failures_non_empty_requires_passed_false(self) -> None:
        """Non-empty failures requires passed=False."""
        with pytest.raises(ValidationError):
            ModelEvaluationResult(
                passed=True,
                score_vector=_passing_score(),
                failures=["some-gate"],  # Non-empty failures with passed=True: invalid
                attribution_refs=[],
            )

    def test_passed_false_with_zero_vector_valid(self) -> None:
        """passed=False + zero vector + non-empty failures is valid."""
        result = ModelEvaluationResult(
            passed=False,
            score_vector=_zero(),
            failures=["gate-budget"],
            attribution_refs=[],
        )
        assert result.passed is False
        assert result.failures == ["gate-budget"]

    def test_passed_true_with_empty_failures_valid(self) -> None:
        """passed=True + non-zero vector + empty failures is valid."""
        result = ModelEvaluationResult(
            passed=True,
            score_vector=_passing_score(),
            failures=[],
            attribution_refs=["item-1"],
        )
        assert result.passed is True
        assert result.failures == []


@pytest.mark.unit
class TestModelEvaluationResultImmutability:
    """Test that ModelEvaluationResult is frozen (immutable)."""

    def test_frozen_raises_on_mutation(self) -> None:
        """Mutating a frozen result raises ValidationError or TypeError."""
        result = ModelEvaluationResult(
            passed=True,
            score_vector=_passing_score(),
            failures=[],
            attribution_refs=[],
        )
        with pytest.raises((ValidationError, TypeError)):
            result.passed = False  # type: ignore[misc]
