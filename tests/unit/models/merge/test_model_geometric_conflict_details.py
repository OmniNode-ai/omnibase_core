# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelGeometricConflictDetails and ModelConflictResolutionResult."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumMergeConflictType
from omnibase_core.models.merge import (
    ModelConflictResolutionResult,
    ModelGeometricConflictDetails,
)


def _make_details(
    *,
    conflict_type: EnumMergeConflictType = EnumMergeConflictType.ORTHOGONAL,
    similarity_score: float = 0.85,
    confidence: float = 0.9,
    explanation: str = "Values modify different aspects",
    affected_fields: list[str] | None = None,
    **kwargs: object,
) -> ModelGeometricConflictDetails:
    """Factory helper for test brevity."""
    return ModelGeometricConflictDetails(
        conflict_type=conflict_type,
        similarity_score=similarity_score,
        confidence=confidence,
        explanation=explanation,
        affected_fields=affected_fields or ["field_a", "field_b"],
        **kwargs,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# ModelGeometricConflictDetails
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelGeometricConflictDetailsConstruction:
    """Tests for constructing ModelGeometricConflictDetails."""

    @pytest.mark.unit
    def test_minimal_construction(self) -> None:
        """Required fields only — optional fields default to None/empty."""
        details = ModelGeometricConflictDetails(
            conflict_type=EnumMergeConflictType.IDENTICAL,
            similarity_score=1.0,
            confidence=0.95,
            explanation="Exact match",
        )
        assert details.conflict_type == EnumMergeConflictType.IDENTICAL
        assert details.similarity_score == 1.0
        assert details.confidence == 0.95
        assert details.explanation == "Exact match"
        assert details.affected_fields == []
        assert details.structural_similarity is None
        assert details.semantic_similarity is None
        assert details.recommended_resolution is None
        assert details.recommended_value is None

    @pytest.mark.unit
    def test_full_construction(self) -> None:
        """All fields populated."""
        details = _make_details(
            conflict_type=EnumMergeConflictType.CONFLICTING,
            similarity_score=0.5,
            confidence=0.7,
            structural_similarity=0.6,
            semantic_similarity=0.4,
            explanation="Partial overlap in output",
            affected_fields=["config.timeout", "config.retries"],
            recommended_resolution="merge_both",
            recommended_value={"timeout": 5000, "retries": 3},
        )
        assert details.structural_similarity == 0.6
        assert details.semantic_similarity == 0.4
        assert details.recommended_resolution == "merge_both"
        assert details.recommended_value == {"timeout": 5000, "retries": 3}
        assert details.affected_fields == ["config.timeout", "config.retries"]


@pytest.mark.unit
class TestModelGeometricConflictDetailsValidation:
    """Tests for field validation on ModelGeometricConflictDetails."""

    @pytest.mark.unit
    def test_similarity_score_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError, match="similarity_score"):
            _make_details(similarity_score=-0.1)

    @pytest.mark.unit
    def test_similarity_score_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError, match="similarity_score"):
            _make_details(similarity_score=1.01)

    @pytest.mark.unit
    def test_confidence_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError, match="confidence"):
            _make_details(confidence=-0.01)

    @pytest.mark.unit
    def test_confidence_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError, match="confidence"):
            _make_details(confidence=1.1)

    @pytest.mark.unit
    def test_structural_similarity_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="structural_similarity"):
            _make_details(structural_similarity=1.5)

    @pytest.mark.unit
    def test_semantic_similarity_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="semantic_similarity"):
            _make_details(semantic_similarity=-0.3)

    @pytest.mark.unit
    def test_similarity_boundary_zero(self) -> None:
        details = _make_details(similarity_score=0.0, confidence=0.0)
        assert details.similarity_score == 0.0
        assert details.confidence == 0.0

    @pytest.mark.unit
    def test_similarity_boundary_one(self) -> None:
        details = _make_details(similarity_score=1.0, confidence=1.0)
        assert details.similarity_score == 1.0
        assert details.confidence == 1.0

    @pytest.mark.unit
    def test_explanation_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError, match="explanation"):
            _make_details(explanation="")

    @pytest.mark.unit
    def test_conflict_type_required(self) -> None:
        with pytest.raises(ValidationError):
            ModelGeometricConflictDetails(
                similarity_score=0.5,
                confidence=0.5,
                explanation="Missing type",
            )  # type: ignore[call-arg]

    @pytest.mark.unit
    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelGeometricConflictDetails(
                conflict_type=EnumMergeConflictType.ORTHOGONAL,
                similarity_score=0.5,
                confidence=0.5,
                explanation="test",
                bogus_field="nope",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelGeometricConflictDetailsImmutability:
    """Tests for frozen model behavior."""

    @pytest.mark.unit
    def test_frozen(self) -> None:
        details = _make_details()
        with pytest.raises(ValidationError):
            details.similarity_score = 0.5  # type: ignore[misc]

    @pytest.mark.unit
    def test_frozen_conflict_type(self) -> None:
        details = _make_details()
        with pytest.raises(ValidationError):
            details.conflict_type = EnumMergeConflictType.IDENTICAL  # type: ignore[misc]


@pytest.mark.unit
class TestModelGeometricConflictDetailsHelpers:
    """Tests for helper methods."""

    @pytest.mark.unit
    def test_requires_human_approval_opposite(self) -> None:
        details = _make_details(conflict_type=EnumMergeConflictType.OPPOSITE)
        assert details.requires_human_approval() is True

    @pytest.mark.unit
    def test_requires_human_approval_ambiguous(self) -> None:
        details = _make_details(conflict_type=EnumMergeConflictType.AMBIGUOUS)
        assert details.requires_human_approval() is True

    @pytest.mark.unit
    def test_does_not_require_human_approval_orthogonal(self) -> None:
        details = _make_details(conflict_type=EnumMergeConflictType.ORTHOGONAL)
        assert details.requires_human_approval() is False

    @pytest.mark.unit
    def test_does_not_require_human_approval_identical(self) -> None:
        details = _make_details(conflict_type=EnumMergeConflictType.IDENTICAL)
        assert details.requires_human_approval() is False

    @pytest.mark.unit
    def test_does_not_require_human_approval_low_conflict(self) -> None:
        details = _make_details(conflict_type=EnumMergeConflictType.LOW_CONFLICT)
        assert details.requires_human_approval() is False

    @pytest.mark.unit
    def test_is_auto_resolvable_orthogonal(self) -> None:
        details = _make_details(conflict_type=EnumMergeConflictType.ORTHOGONAL)
        assert details.is_auto_resolvable() is True

    @pytest.mark.unit
    def test_is_auto_resolvable_identical(self) -> None:
        details = _make_details(conflict_type=EnumMergeConflictType.IDENTICAL)
        assert details.is_auto_resolvable() is True

    @pytest.mark.unit
    def test_is_auto_resolvable_low_conflict(self) -> None:
        details = _make_details(conflict_type=EnumMergeConflictType.LOW_CONFLICT)
        assert details.is_auto_resolvable() is True

    @pytest.mark.unit
    def test_not_auto_resolvable_opposite(self) -> None:
        details = _make_details(conflict_type=EnumMergeConflictType.OPPOSITE)
        assert details.is_auto_resolvable() is False

    @pytest.mark.unit
    def test_not_auto_resolvable_ambiguous(self) -> None:
        details = _make_details(conflict_type=EnumMergeConflictType.AMBIGUOUS)
        assert details.is_auto_resolvable() is False

    @pytest.mark.unit
    def test_not_auto_resolvable_conflicting(self) -> None:
        """CONFLICTING is partially resolvable, not fully auto."""
        details = _make_details(conflict_type=EnumMergeConflictType.CONFLICTING)
        assert details.is_auto_resolvable() is False


@pytest.mark.unit
class TestModelGeometricConflictDetailsRepresentation:
    """Tests for __str__ and __repr__."""

    @pytest.mark.unit
    def test_str(self) -> None:
        details = _make_details(similarity_score=0.85, confidence=0.90)
        result = str(details)
        assert "orthogonal" in result
        assert "0.85" in result
        assert "0.90" in result

    @pytest.mark.unit
    def test_repr(self) -> None:
        details = _make_details()
        result = repr(details)
        assert "ModelGeometricConflictDetails" in result
        assert "ORTHOGONAL" in result


@pytest.mark.unit
class TestModelGeometricConflictDetailsSerialization:
    """Tests for serialization roundtrip."""

    @pytest.mark.unit
    def test_model_dump(self) -> None:
        details = _make_details()
        data = details.model_dump()
        assert data["conflict_type"] == EnumMergeConflictType.ORTHOGONAL
        assert data["similarity_score"] == 0.85
        assert data["confidence"] == 0.9
        assert data["explanation"] == "Values modify different aspects"

    @pytest.mark.unit
    def test_model_validate_roundtrip(self) -> None:
        details = _make_details(structural_similarity=0.7, semantic_similarity=0.8)
        data = details.model_dump()
        restored = ModelGeometricConflictDetails.model_validate(data)
        assert restored == details

    @pytest.mark.unit
    def test_model_validate_from_dict(self) -> None:
        data = {
            "conflict_type": "orthogonal",
            "similarity_score": 0.5,
            "confidence": 0.6,
            "explanation": "test",
        }
        details = ModelGeometricConflictDetails.model_validate(data)
        assert details.conflict_type == EnumMergeConflictType.ORTHOGONAL

    @pytest.mark.unit
    def test_from_attributes(self) -> None:
        class DetailsLike:
            conflict_type = EnumMergeConflictType.IDENTICAL
            similarity_score = 1.0
            confidence = 0.99
            structural_similarity = None
            semantic_similarity = None
            explanation = "Exact match"
            affected_fields: list[str] = []
            recommended_resolution = None
            recommended_value = None

        obj = DetailsLike()
        details = ModelGeometricConflictDetails.model_validate(
            obj, from_attributes=True
        )
        assert details.conflict_type == EnumMergeConflictType.IDENTICAL
        assert details.similarity_score == 1.0


# ---------------------------------------------------------------------------
# ModelConflictResolutionResult
# ---------------------------------------------------------------------------


def _make_result(
    *,
    conflict_type: EnumMergeConflictType = EnumMergeConflictType.ORTHOGONAL,
    required_human_approval: bool = False,
    human_approved: bool = False,
    resolved_value: object = "merged_value",
    resolution_strategy: str = "auto_merge",
) -> ModelConflictResolutionResult:
    """Factory helper for test brevity."""
    details = _make_details(conflict_type=conflict_type)
    return ModelConflictResolutionResult(
        details=details,
        resolved_value=resolved_value,
        resolution_strategy=resolution_strategy,
        required_human_approval=required_human_approval,
        human_approved=human_approved,
    )


@pytest.mark.unit
class TestModelConflictResolutionResultConstruction:
    """Tests for constructing ModelConflictResolutionResult."""

    @pytest.mark.unit
    def test_auto_resolved(self) -> None:
        result = _make_result()
        assert result.resolution_strategy == "auto_merge"
        assert result.required_human_approval is False
        assert result.human_approved is False
        assert result.resolved_value == "merged_value"

    @pytest.mark.unit
    def test_human_approved(self) -> None:
        result = _make_result(
            conflict_type=EnumMergeConflictType.OPPOSITE,
            required_human_approval=True,
            human_approved=True,
            resolution_strategy="human_decision",
        )
        assert result.required_human_approval is True
        assert result.human_approved is True

    @pytest.mark.unit
    def test_human_default_false(self) -> None:
        """human_approved defaults to False."""
        result = _make_result(
            conflict_type=EnumMergeConflictType.OPPOSITE,
            required_human_approval=True,
        )
        assert result.human_approved is False


@pytest.mark.unit
class TestModelConflictResolutionResultGI3:
    """GI-3 invariant: OPPOSITE and AMBIGUOUS must require human approval."""

    @pytest.mark.unit
    def test_opposite_requires_approval(self) -> None:
        with pytest.raises(ValidationError, match="GI-3"):
            _make_result(
                conflict_type=EnumMergeConflictType.OPPOSITE,
                required_human_approval=False,
            )

    @pytest.mark.unit
    def test_ambiguous_requires_approval(self) -> None:
        with pytest.raises(ValidationError, match="GI-3"):
            _make_result(
                conflict_type=EnumMergeConflictType.AMBIGUOUS,
                required_human_approval=False,
            )

    @pytest.mark.unit
    def test_opposite_with_approval_succeeds(self) -> None:
        result = _make_result(
            conflict_type=EnumMergeConflictType.OPPOSITE,
            required_human_approval=True,
        )
        assert result.required_human_approval is True

    @pytest.mark.unit
    def test_ambiguous_with_approval_succeeds(self) -> None:
        result = _make_result(
            conflict_type=EnumMergeConflictType.AMBIGUOUS,
            required_human_approval=True,
        )
        assert result.required_human_approval is True

    @pytest.mark.unit
    def test_orthogonal_no_approval_ok(self) -> None:
        """Non-GI-3 types can skip human approval."""
        result = _make_result(
            conflict_type=EnumMergeConflictType.ORTHOGONAL,
            required_human_approval=False,
        )
        assert result.required_human_approval is False

    @pytest.mark.unit
    def test_identical_no_approval_ok(self) -> None:
        result = _make_result(
            conflict_type=EnumMergeConflictType.IDENTICAL,
            required_human_approval=False,
        )
        assert result.required_human_approval is False

    @pytest.mark.unit
    def test_conflicting_no_approval_ok(self) -> None:
        """CONFLICTING is partially auto-resolvable, no GI-3 mandate."""
        result = _make_result(
            conflict_type=EnumMergeConflictType.CONFLICTING,
            required_human_approval=False,
        )
        assert result.required_human_approval is False


@pytest.mark.unit
class TestModelConflictResolutionResultValidation:
    """Tests for field validation."""

    @pytest.mark.unit
    def test_resolution_strategy_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError, match="resolution_strategy"):
            details = _make_details()
            ModelConflictResolutionResult(
                details=details,
                resolved_value="x",
                resolution_strategy="",
                required_human_approval=False,
            )

    @pytest.mark.unit
    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            details = _make_details()
            ModelConflictResolutionResult(
                details=details,
                resolved_value="x",
                resolution_strategy="auto",
                required_human_approval=False,
                bogus="nope",  # type: ignore[call-arg]
            )

    @pytest.mark.unit
    def test_frozen(self) -> None:
        result = _make_result()
        with pytest.raises(ValidationError):
            result.human_approved = True  # type: ignore[misc]


@pytest.mark.unit
class TestModelConflictResolutionResultRepresentation:
    """Tests for __str__ and __repr__."""

    @pytest.mark.unit
    def test_str_auto(self) -> None:
        result = _make_result()
        assert "auto" in str(result)

    @pytest.mark.unit
    def test_str_pending(self) -> None:
        result = _make_result(
            conflict_type=EnumMergeConflictType.OPPOSITE,
            required_human_approval=True,
            human_approved=False,
        )
        assert "pending" in str(result)

    @pytest.mark.unit
    def test_str_approved(self) -> None:
        result = _make_result(
            conflict_type=EnumMergeConflictType.OPPOSITE,
            required_human_approval=True,
            human_approved=True,
        )
        assert "approved" in str(result)

    @pytest.mark.unit
    def test_repr(self) -> None:
        result = _make_result()
        r = repr(result)
        assert "ModelConflictResolutionResult" in r
        assert "auto_merge" in r


@pytest.mark.unit
class TestModelConflictResolutionResultSerialization:
    """Tests for serialization."""

    @pytest.mark.unit
    def test_model_dump(self) -> None:
        result = _make_result()
        data = result.model_dump()
        assert data["resolution_strategy"] == "auto_merge"
        assert data["details"]["conflict_type"] == EnumMergeConflictType.ORTHOGONAL

    @pytest.mark.unit
    def test_model_validate_roundtrip(self) -> None:
        result = _make_result(
            conflict_type=EnumMergeConflictType.OPPOSITE,
            required_human_approval=True,
            human_approved=True,
            resolution_strategy="human_decision",
        )
        data = result.model_dump()
        restored = ModelConflictResolutionResult.model_validate(data)
        assert restored == result
