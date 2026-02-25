# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelScoreVector.

Tests cover: model construction, zero() classmethod, immutability,
and field validation constraints. Part of OMN-2537.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.objective.model_score_vector import ModelScoreVector


@pytest.mark.unit
class TestModelScoreVectorCreation:
    """Test ModelScoreVector instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Create a score vector with all fields specified."""
        vec = ModelScoreVector(
            correctness=1.0,
            safety=0.9,
            cost=0.8,
            latency=0.7,
            maintainability=0.6,
            human_time=0.5,
        )
        assert vec.correctness == 1.0
        assert vec.safety == 0.9
        assert vec.cost == 0.8
        assert vec.latency == 0.7
        assert vec.maintainability == 0.6
        assert vec.human_time == 0.5

    def test_create_with_boundary_values(self) -> None:
        """All fields at boundary values (0.0 and 1.0) are valid."""
        vec_min = ModelScoreVector(
            correctness=0.0,
            safety=0.0,
            cost=0.0,
            latency=0.0,
            maintainability=0.0,
            human_time=0.0,
        )
        vec_max = ModelScoreVector(
            correctness=1.0,
            safety=1.0,
            cost=1.0,
            latency=1.0,
            maintainability=1.0,
            human_time=1.0,
        )
        assert vec_min.correctness == 0.0
        assert vec_max.correctness == 1.0


@pytest.mark.unit
class TestModelScoreVectorZero:
    """Test ModelScoreVector.zero() classmethod."""

    def test_zero_returns_all_zero_fields(self) -> None:
        """zero() should return a vector with all fields == 0.0."""
        zero = ModelScoreVector.zero()
        assert zero.correctness == 0.0
        assert zero.safety == 0.0
        assert zero.cost == 0.0
        assert zero.latency == 0.0
        assert zero.maintainability == 0.0
        assert zero.human_time == 0.0

    def test_zero_is_frozen(self) -> None:
        """zero() result is frozen (immutable)."""
        zero = ModelScoreVector.zero()
        with pytest.raises((ValidationError, TypeError)):
            zero.correctness = 1.0  # type: ignore[misc]

    def test_zero_equals_manual_zero(self) -> None:
        """zero() result equals a manually constructed all-zero vector."""
        zero_auto = ModelScoreVector.zero()
        zero_manual = ModelScoreVector(
            correctness=0.0,
            safety=0.0,
            cost=0.0,
            latency=0.0,
            maintainability=0.0,
            human_time=0.0,
        )
        assert zero_auto == zero_manual

    def test_zero_idempotent(self) -> None:
        """Calling zero() multiple times returns equal vectors."""
        assert ModelScoreVector.zero() == ModelScoreVector.zero()


@pytest.mark.unit
class TestModelScoreVectorImmutability:
    """Test that ModelScoreVector is frozen (immutable)."""

    def test_frozen_raises_on_mutation(self) -> None:
        """Mutating a frozen model raises ValidationError or TypeError."""
        vec = ModelScoreVector(
            correctness=1.0,
            safety=1.0,
            cost=1.0,
            latency=1.0,
            maintainability=1.0,
            human_time=1.0,
        )
        with pytest.raises((ValidationError, TypeError)):
            vec.correctness = 0.5  # type: ignore[misc]


@pytest.mark.unit
class TestModelScoreVectorValidation:
    """Test field validation constraints."""

    def test_field_above_one_raises(self) -> None:
        """A field value > 1.0 should raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelScoreVector(
                correctness=1.1,  # Invalid
                safety=0.0,
                cost=0.0,
                latency=0.0,
                maintainability=0.0,
                human_time=0.0,
            )

    def test_field_below_zero_raises(self) -> None:
        """A field value < 0.0 should raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelScoreVector(
                correctness=0.0,
                safety=-0.1,  # Invalid
                cost=0.0,
                latency=0.0,
                maintainability=0.0,
                human_time=0.0,
            )

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields are rejected due to extra='forbid'."""
        with pytest.raises(ValidationError):
            ModelScoreVector(  # type: ignore[call-arg]
                correctness=1.0,
                safety=1.0,
                cost=1.0,
                latency=1.0,
                maintainability=1.0,
                human_time=1.0,
                unknown_field=0.5,  # Extra field
            )
