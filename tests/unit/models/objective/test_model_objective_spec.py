# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelObjectiveSpec and supporting models.

Tests cover: construction, lexicographic_priority validation,
ModelGateSpec, ModelShapedTermSpec, and ModelScoreRange.
Part of OMN-2537.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_gate_type import EnumGateType
from omnibase_core.models.objective.model_gate_spec import ModelGateSpec
from omnibase_core.models.objective.model_objective_spec import ModelObjectiveSpec
from omnibase_core.models.objective.model_score_range import ModelScoreRange
from omnibase_core.models.objective.model_shaped_term_spec import ModelShapedTermSpec


def _default_gates() -> list[ModelGateSpec]:
    return [
        ModelGateSpec(
            id="gate-tests", type=EnumGateType.TEST_PASS, threshold=1.0, weight=1.0
        ),
        ModelGateSpec(
            id="gate-budget", type=EnumGateType.BUDGET, threshold=0.95, weight=0.5
        ),
    ]


def _default_shaped_terms() -> list[ModelShapedTermSpec]:
    return [
        ModelShapedTermSpec(id="term-cost", weight=1.0, direction="minimize"),
        ModelShapedTermSpec(id="term-latency", weight=0.5, direction="minimize"),
    ]


def _default_score_range() -> ModelScoreRange:
    return ModelScoreRange(min=0.0, max=1.0)


@pytest.mark.unit
class TestModelObjectiveSpecConstruction:
    """Test ModelObjectiveSpec instantiation."""

    def test_create_valid_objective_spec(self) -> None:
        """Create a valid ObjectiveSpec with all required fields."""
        spec = ModelObjectiveSpec(
            objective_id="omniclaude.task.v1",
            version="1.0.0",
            gates=_default_gates(),
            shaped_terms=_default_shaped_terms(),
            score_range=_default_score_range(),
            lexicographic_priority=["correctness", "safety", "cost"],
        )
        assert spec.objective_id == "omniclaude.task.v1"
        assert spec.version == "1.0.0"
        assert len(spec.gates) == 2
        assert len(spec.shaped_terms) == 2

    def test_create_with_empty_gates_and_terms(self) -> None:
        """ObjectiveSpec with empty gates and shaped_terms is structurally valid."""
        spec = ModelObjectiveSpec(
            objective_id="empty.spec.v1",
            version="1.0.0",
            gates=[],
            shaped_terms=[],
            score_range=_default_score_range(),
            lexicographic_priority=["correctness"],
        )
        assert spec.gates == []
        assert spec.shaped_terms == []


@pytest.mark.unit
class TestModelObjectiveSpecLexicographicPriority:
    """Test lexicographic_priority validation."""

    def test_valid_priority_all_fields(self) -> None:
        """All six valid ScoreVector fields are accepted."""
        spec = ModelObjectiveSpec(
            objective_id="test.spec.v1",
            version="1.0.0",
            gates=[],
            shaped_terms=[],
            score_range=_default_score_range(),
            lexicographic_priority=[
                "correctness",
                "safety",
                "cost",
                "latency",
                "maintainability",
                "human_time",
            ],
        )
        assert len(spec.lexicographic_priority) == 6

    def test_invalid_priority_field_raises(self) -> None:
        """An invalid field name in lexicographic_priority raises ValidationError."""
        with pytest.raises(ValidationError, match="lexicographic_priority"):
            ModelObjectiveSpec(
                objective_id="test.spec.v1",
                version="1.0.0",
                gates=[],
                shaped_terms=[],
                score_range=_default_score_range(),
                lexicographic_priority=["correctness", "invalid_field"],
            )

    def test_empty_priority_list_valid(self) -> None:
        """Empty lexicographic_priority is structurally valid (no ordering declared)."""
        spec = ModelObjectiveSpec(
            objective_id="test.spec.v1",
            version="1.0.0",
            gates=[],
            shaped_terms=[],
            score_range=_default_score_range(),
            lexicographic_priority=[],
        )
        assert spec.lexicographic_priority == []


@pytest.mark.unit
class TestModelObjectiveSpecImmutability:
    """Test that ModelObjectiveSpec is frozen (immutable)."""

    def test_frozen_raises_on_mutation(self) -> None:
        """Mutating a frozen spec raises ValidationError or TypeError."""
        spec = ModelObjectiveSpec(
            objective_id="test.spec.v1",
            version="1.0.0",
            gates=[],
            shaped_terms=[],
            score_range=_default_score_range(),
            lexicographic_priority=["correctness"],
        )
        with pytest.raises((ValidationError, TypeError)):
            spec.version = "2.0.0"  # type: ignore[misc]


@pytest.mark.unit
class TestModelScoreRange:
    """Test ModelScoreRange validation."""

    def test_valid_range(self) -> None:
        """min < max is valid."""
        r = ModelScoreRange(min=0.0, max=1.0)
        assert r.min == 0.0
        assert r.max == 1.0

    def test_negative_range_valid(self) -> None:
        """Negative min with positive max is valid."""
        r = ModelScoreRange(min=-1.0, max=1.0)
        assert r.min == -1.0

    def test_min_equals_max_raises(self) -> None:
        """min == max raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelScoreRange(min=1.0, max=1.0)

    def test_min_greater_than_max_raises(self) -> None:
        """min > max raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelScoreRange(min=2.0, max=1.0)


@pytest.mark.unit
class TestModelGateSpec:
    """Test ModelGateSpec validation."""

    def test_create_valid_gate(self) -> None:
        """Create a valid GateSpec."""
        gate = ModelGateSpec(
            id="gate-tests",
            type=EnumGateType.TEST_PASS,
            threshold=1.0,
            weight=1.0,
        )
        assert gate.id == "gate-tests"
        assert gate.type == EnumGateType.TEST_PASS

    def test_zero_weight_raises(self) -> None:
        """weight=0.0 raises ValidationError (must be > 0)."""
        with pytest.raises(ValidationError):
            ModelGateSpec(
                id="gate-tests",
                type=EnumGateType.TEST_PASS,
                threshold=1.0,
                weight=0.0,
            )

    def test_frozen(self) -> None:
        """GateSpec is frozen."""
        gate = ModelGateSpec(
            id="gate-tests",
            type=EnumGateType.TEST_PASS,
            threshold=1.0,
            weight=1.0,
        )
        with pytest.raises((ValidationError, TypeError)):
            gate.weight = 2.0  # type: ignore[misc]


@pytest.mark.unit
class TestModelShapedTermSpec:
    """Test ModelShapedTermSpec validation."""

    def test_create_maximize(self) -> None:
        """Create a maximize shaped term."""
        term = ModelShapedTermSpec(id="term-review", weight=1.0, direction="maximize")
        assert term.direction == "maximize"

    def test_create_minimize(self) -> None:
        """Create a minimize shaped term."""
        term = ModelShapedTermSpec(id="term-cost", weight=0.5, direction="minimize")
        assert term.direction == "minimize"

    def test_invalid_direction_raises(self) -> None:
        """Invalid direction raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelShapedTermSpec(
                id="term-cost",
                weight=1.0,
                direction="neutral",  # type: ignore[arg-type]  # Invalid
            )

    def test_zero_weight_raises(self) -> None:
        """weight=0.0 raises ValidationError (must be > 0)."""
        with pytest.raises(ValidationError):
            ModelShapedTermSpec(id="term-cost", weight=0.0, direction="minimize")
