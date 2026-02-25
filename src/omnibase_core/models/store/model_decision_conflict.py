# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelDecisionConflict - Detected conflict between two Decision Store entries.

Represents a detected or assessed conflict between two decisions in the
Decision Store. Uses an ordered-pair pattern (decision_min_id < decision_max_id)
to prevent duplicate conflict records for the same pair of decisions.

.. versionadded:: 0.7.0
    Added as part of Decision Store infrastructure (OMN-2763)
"""

from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelDecisionConflict(BaseModel):
    """A detected conflict between two Decision Store entries.

    Represents a structural or semantic conflict between two decisions.
    The (decision_min_id, decision_max_id) pair is enforced as an ordered
    pair (min < max) to prevent duplicate conflict records for the same
    pair of decisions.

    Attributes:
        conflict_id: Unique identifier for this conflict record.
        decision_min_id: UUID of the lexicographically smaller decision.
        decision_max_id: UUID of the lexicographically larger decision.
        structural_confidence: Confidence score (0.0-1.0) from structural analysis.
        semantic_verdict: LLM or human verdict on whether conflict is real; None
            if semantic analysis has not been run.
        semantic_explanation: Human-readable explanation from semantic analysis.
        final_severity: Assessed severity of the conflict.
        status: Lifecycle status of the conflict record.

    Example:
        >>> from uuid import uuid4
        >>> id_a = uuid4()
        >>> id_b = uuid4()
        >>> low, high = (id_a, id_b) if str(id_a) < str(id_b) else (id_b, id_a)
        >>> conflict = ModelDecisionConflict(
        ...     decision_min_id=low,
        ...     decision_max_id=high,
        ...     structural_confidence=0.87,
        ...     final_severity="HIGH",
        ...     status="OPEN",
        ... )
        >>> conflict.status
        'OPEN'

    .. versionadded:: 0.7.0
        Added as part of Decision Store infrastructure (OMN-2763)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # === Identity ===

    conflict_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this conflict record.",
    )

    # === Ordered Decision Pair ===

    decision_min_id: UUID = Field(
        ...,
        description=(
            "UUID of the lexicographically smaller decision in the conflicting pair. "
            "Must be strictly less than decision_max_id to prevent duplicate records."
        ),
    )

    decision_max_id: UUID = Field(
        ...,
        description=(
            "UUID of the lexicographically larger decision in the conflicting pair. "
            "Must be strictly greater than decision_min_id."
        ),
    )

    # === Structural Analysis ===

    structural_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score from structural conflict analysis (0.0-1.0).",
    )

    # === Semantic Analysis (optional) ===

    semantic_verdict: bool | None = Field(
        default=None,
        description=(
            "LLM or human verdict: True if conflict is real, False if dismissed. "
            "None if semantic analysis has not been performed."
        ),
    )

    semantic_explanation: str | None = Field(
        default=None,
        description="Human-readable explanation from semantic analysis, if performed.",
    )

    # === Resolution ===

    final_severity: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        ...,
        description="Assessed severity level of this conflict.",
    )

    status: Literal["OPEN", "DISMISSED", "RESOLVED"] = Field(
        ...,
        description="Lifecycle status of this conflict record.",
    )

    # === Validators ===

    @model_validator(mode="after")
    def validate_ordered_pair(self) -> "ModelDecisionConflict":
        """Validate that decision_min_id < decision_max_id (lexicographic order).

        The ordered-pair invariant prevents duplicate conflict records for the
        same pair of decisions. Callers must sort the pair before construction.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If decision_min_id >= decision_max_id.
        """
        if str(self.decision_min_id) >= str(self.decision_max_id):
            raise ValueError(
                f"decision_min_id must be strictly less than decision_max_id "
                f"(lexicographic order). Got: "
                f"min={self.decision_min_id!r}, max={self.decision_max_id!r}. "
                "Sort the pair before constructing ModelDecisionConflict."
            )
        return self

    @model_validator(mode="after")
    def validate_semantic_consistency(self) -> "ModelDecisionConflict":
        """Validate semantic_verdict and semantic_explanation consistency.

        When semantic_verdict is set, semantic_explanation should also be set.
        When semantic_explanation is set, semantic_verdict should also be set.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If semantic_verdict and semantic_explanation are inconsistent.
        """
        verdict_set = self.semantic_verdict is not None
        explanation_set = self.semantic_explanation is not None
        if verdict_set != explanation_set:
            raise ValueError(
                "semantic_verdict and semantic_explanation must both be set or "
                "both be None; they cannot be mixed. "
                f"Got: semantic_verdict={self.semantic_verdict!r}, "
                f"semantic_explanation={self.semantic_explanation!r}"
            )
        return self


__all__ = ["ModelDecisionConflict"]
