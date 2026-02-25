# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelDecisionConflict.

Tests:
- Valid construction with all required fields
- Ordered-pair invariant: decision_min_id must be < decision_max_id
- structural_confidence bounds (0.0-1.0)
- semantic_verdict and semantic_explanation consistency
- All valid status and severity literal values
- Immutability (frozen model)
- Extra fields forbidden
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.models.store.model_decision_conflict import ModelDecisionConflict

# ============================================================================
# Helper to produce a valid ordered pair
# ============================================================================


def _ordered_pair() -> tuple[UUID, UUID]:
    """Generate two UUIDs in lexicographic order (min, max)."""
    ids = [uuid4(), uuid4()]
    ids.sort(key=str)
    return ids[0], ids[1]


# ============================================================================
# Valid construction
# ============================================================================


class TestModelDecisionConflictValid:
    """Tests for valid ModelDecisionConflict construction."""

    def test_basic_construction(self) -> None:
        min_id, max_id = _ordered_pair()
        conflict = ModelDecisionConflict(
            decision_min_id=min_id,
            decision_max_id=max_id,
            structural_confidence=0.75,
            final_severity="HIGH",
            status="OPEN",
        )
        assert conflict.decision_min_id == min_id
        assert conflict.decision_max_id == max_id
        assert conflict.structural_confidence == 0.75
        assert conflict.final_severity == "HIGH"
        assert conflict.status == "OPEN"
        assert conflict.semantic_verdict is None
        assert conflict.semantic_explanation is None

    def test_default_conflict_id_generated(self) -> None:
        min_id, max_id = _ordered_pair()
        conflict = ModelDecisionConflict(
            decision_min_id=min_id,
            decision_max_id=max_id,
            structural_confidence=0.5,
            final_severity="MEDIUM",
            status="DISMISSED",
        )
        assert isinstance(conflict.conflict_id, UUID)

    def test_custom_conflict_id_accepted(self) -> None:
        min_id, max_id = _ordered_pair()
        custom_id = uuid4()
        conflict = ModelDecisionConflict(
            conflict_id=custom_id,
            decision_min_id=min_id,
            decision_max_id=max_id,
            structural_confidence=0.3,
            final_severity="LOW",
            status="RESOLVED",
        )
        assert conflict.conflict_id == custom_id

    def test_with_semantic_analysis(self) -> None:
        min_id, max_id = _ordered_pair()
        conflict = ModelDecisionConflict(
            decision_min_id=min_id,
            decision_max_id=max_id,
            structural_confidence=0.9,
            semantic_verdict=True,
            semantic_explanation="Confirmed: both decisions mandate different transports.",
            final_severity="HIGH",
            status="OPEN",
        )
        assert conflict.semantic_verdict is True
        assert "transports" in conflict.semantic_explanation  # type: ignore[operator]

    def test_semantic_verdict_false(self) -> None:
        min_id, max_id = _ordered_pair()
        conflict = ModelDecisionConflict(
            decision_min_id=min_id,
            decision_max_id=max_id,
            structural_confidence=0.4,
            semantic_verdict=False,
            semantic_explanation="False positive: different layers, no real conflict.",
            final_severity="LOW",
            status="DISMISSED",
        )
        assert conflict.semantic_verdict is False

    def test_frozen_immutable(self) -> None:
        min_id, max_id = _ordered_pair()
        conflict = ModelDecisionConflict(
            decision_min_id=min_id,
            decision_max_id=max_id,
            structural_confidence=0.5,
            final_severity="MEDIUM",
            status="OPEN",
        )
        with pytest.raises(Exception):
            conflict.status = "RESOLVED"  # type: ignore[misc]

    @pytest.mark.parametrize("status", ["OPEN", "DISMISSED", "RESOLVED"])
    def test_all_statuses_valid(self, status: str) -> None:
        min_id, max_id = _ordered_pair()
        conflict = ModelDecisionConflict(
            decision_min_id=min_id,
            decision_max_id=max_id,
            structural_confidence=0.5,
            final_severity="MEDIUM",
            status=status,  # type: ignore[arg-type]
        )
        assert conflict.status == status

    @pytest.mark.parametrize("severity", ["HIGH", "MEDIUM", "LOW"])
    def test_all_severities_valid(self, severity: str) -> None:
        min_id, max_id = _ordered_pair()
        conflict = ModelDecisionConflict(
            decision_min_id=min_id,
            decision_max_id=max_id,
            structural_confidence=0.5,
            final_severity=severity,  # type: ignore[arg-type]
            status="OPEN",
        )
        assert conflict.final_severity == severity


# ============================================================================
# Ordered-pair invariant
# ============================================================================


class TestOrderedPairInvariant:
    """Tests for the decision_min_id < decision_max_id invariant."""

    def test_min_greater_than_max_raises(self) -> None:
        min_id, max_id = _ordered_pair()
        # Swap to violate the invariant
        with pytest.raises(ValidationError, match="strictly less than"):
            ModelDecisionConflict(
                decision_min_id=max_id,  # wrong order
                decision_max_id=min_id,
                structural_confidence=0.5,
                final_severity="MEDIUM",
                status="OPEN",
            )

    def test_equal_ids_raises(self) -> None:
        same_id = uuid4()
        with pytest.raises(ValidationError, match="strictly less than"):
            ModelDecisionConflict(
                decision_min_id=same_id,
                decision_max_id=same_id,
                structural_confidence=0.5,
                final_severity="MEDIUM",
                status="OPEN",
            )


# ============================================================================
# structural_confidence bounds
# ============================================================================


class TestStructuralConfidenceBounds:
    """Tests for structural_confidence 0.0-1.0 bounds."""

    def test_zero_confidence_valid(self) -> None:
        min_id, max_id = _ordered_pair()
        conflict = ModelDecisionConflict(
            decision_min_id=min_id,
            decision_max_id=max_id,
            structural_confidence=0.0,
            final_severity="LOW",
            status="OPEN",
        )
        assert conflict.structural_confidence == 0.0

    def test_one_confidence_valid(self) -> None:
        min_id, max_id = _ordered_pair()
        conflict = ModelDecisionConflict(
            decision_min_id=min_id,
            decision_max_id=max_id,
            structural_confidence=1.0,
            final_severity="HIGH",
            status="OPEN",
        )
        assert conflict.structural_confidence == 1.0

    def test_negative_confidence_raises(self) -> None:
        min_id, max_id = _ordered_pair()
        with pytest.raises(ValidationError):
            ModelDecisionConflict(
                decision_min_id=min_id,
                decision_max_id=max_id,
                structural_confidence=-0.1,
                final_severity="LOW",
                status="OPEN",
            )

    def test_over_one_confidence_raises(self) -> None:
        min_id, max_id = _ordered_pair()
        with pytest.raises(ValidationError):
            ModelDecisionConflict(
                decision_min_id=min_id,
                decision_max_id=max_id,
                structural_confidence=1.1,
                final_severity="LOW",
                status="OPEN",
            )


# ============================================================================
# Semantic consistency validation
# ============================================================================


class TestSemanticConsistency:
    """Tests for semantic_verdict and semantic_explanation consistency."""

    def test_verdict_without_explanation_raises(self) -> None:
        min_id, max_id = _ordered_pair()
        with pytest.raises(ValidationError, match="both be set or both be None"):
            ModelDecisionConflict(
                decision_min_id=min_id,
                decision_max_id=max_id,
                structural_confidence=0.8,
                semantic_verdict=True,
                # missing semantic_explanation
                final_severity="HIGH",
                status="OPEN",
            )

    def test_explanation_without_verdict_raises(self) -> None:
        min_id, max_id = _ordered_pair()
        with pytest.raises(ValidationError, match="both be set or both be None"):
            ModelDecisionConflict(
                decision_min_id=min_id,
                decision_max_id=max_id,
                structural_confidence=0.8,
                semantic_explanation="Only explanation, no verdict",
                final_severity="HIGH",
                status="OPEN",
            )


# ============================================================================
# Schema enforcement
# ============================================================================


class TestSchemaEnforcement:
    """Tests for extra fields forbidden and invalid literals."""

    def test_extra_fields_forbidden(self) -> None:
        min_id, max_id = _ordered_pair()
        with pytest.raises(ValidationError):
            ModelDecisionConflict(  # type: ignore[call-arg]
                decision_min_id=min_id,
                decision_max_id=max_id,
                structural_confidence=0.5,
                final_severity="MEDIUM",
                status="OPEN",
                unexpected_field="bad",
            )

    def test_invalid_severity_raises(self) -> None:
        min_id, max_id = _ordered_pair()
        with pytest.raises(ValidationError):
            ModelDecisionConflict(
                decision_min_id=min_id,
                decision_max_id=max_id,
                structural_confidence=0.5,
                final_severity="CRITICAL",  # type: ignore[arg-type]
                status="OPEN",
            )

    def test_invalid_status_raises(self) -> None:
        min_id, max_id = _ordered_pair()
        with pytest.raises(ValidationError):
            ModelDecisionConflict(
                decision_min_id=min_id,
                decision_max_id=max_id,
                structural_confidence=0.5,
                final_severity="HIGH",
                status="PENDING",  # type: ignore[arg-type]
            )
