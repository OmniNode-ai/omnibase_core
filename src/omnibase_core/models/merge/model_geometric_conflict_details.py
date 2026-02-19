# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Geometric Conflict Details Model for Parallel Agent Output Analysis.

This module defines ModelGeometricConflictDetails for rich conflict analysis
beyond coarse enum classification. Stores fine-grained similarity metrics
and advisory recommendations for parallel agent output conflicts.

Global Invariant GI-3:
    recommended_resolution is ADVISORY ONLY. Callers must not treat
    recommendations as authoritative. OPPOSITE and AMBIGUOUS conflicts
    MUST require human approval for resolution.

See Also:
    - OMN-1853: ModelGeometricConflictDetails implementation
    - OMN-1852: EnumMergeConflictType geometric types
    - ModelMergeConflict: Coarse conflict model for contract merging
    - ModelConflictResolutionResult: Resolution tracking model

.. versionadded:: 0.16.1
    Added as part of geometric conflict analysis (OMN-1853)
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_merge_conflict_type import EnumMergeConflictType

# Conflict types that MUST require human approval (GI-3).
# Shared by ModelGeometricConflictDetails and ModelConflictResolutionResult.
HUMAN_APPROVAL_REQUIRED_TYPES = frozenset(
    {
        EnumMergeConflictType.OPPOSITE,
        EnumMergeConflictType.AMBIGUOUS,
    }
)

# Conflict types that permit fully automated resolution (no human approval needed).
AUTO_RESOLVABLE_TYPES = frozenset(
    {
        EnumMergeConflictType.IDENTICAL,
        EnumMergeConflictType.ORTHOGONAL,
        EnumMergeConflictType.LOW_CONFLICT,
    }
)


class ModelGeometricConflictDetails(BaseModel):
    """
    Rich conflict analysis for parallel agent output classification.

    Provides fine-grained similarity metrics, multi-axis analysis, and
    advisory recommendations beyond the coarse EnumMergeConflictType.

    GI-3: recommended_resolution is ADVISORY ONLY. Automated resolution
    is only permitted for ORTHOGONAL, LOW_CONFLICT, and IDENTICAL types.

    Thread Safety:
        Immutable (frozen=True) and safe for concurrent access.

    .. versionadded:: 0.16.1
        Added as part of geometric conflict analysis (OMN-1853)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        validate_assignment=True,
    )

    conflict_type: EnumMergeConflictType = Field(
        ...,
        description="Coarse geometric classification of the conflict",
    )

    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall similarity between agent outputs (0.0=opposite, 1.0=identical)",
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Classifier confidence in the conflict_type assignment",
    )

    structural_similarity: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Structural similarity axis (shape, schema, keys)",
    )

    semantic_similarity: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Semantic similarity axis (meaning, intent)",
    )

    explanation: str = Field(
        ...,
        min_length=1,
        description="Human-readable explanation of the classification",
    )

    affected_fields: list[str] = Field(
        default_factory=list,
        description="Dot-notation field paths involved in the conflict",
    )

    recommended_resolution: str | None = Field(
        default=None,
        description="ADVISORY resolution suggestion (GI-3: not authoritative)",
    )

    recommended_value: Any = Field(
        default=None,
        description=(
            "ADVISORY suggested resolved value (GI-3: not authoritative). "
            "Callers must not mutate this value in-place; frozen=True prevents "
            "reassignment but not deep mutation of mutable payloads."
        ),
    )

    def requires_human_approval(self) -> bool:
        """Whether this conflict type mandates human approval (GI-3)."""
        return self.conflict_type in HUMAN_APPROVAL_REQUIRED_TYPES

    def is_auto_resolvable(self) -> bool:
        """Whether this conflict type permits fully automated resolution."""
        return self.conflict_type in AUTO_RESOLVABLE_TYPES

    def __str__(self) -> str:
        return (
            f"GeometricConflict({self.conflict_type.value}, "
            f"similarity={self.similarity_score:.2f}, "
            f"confidence={self.confidence:.2f})"
        )

    def __repr__(self) -> str:
        return (
            f"ModelGeometricConflictDetails("
            f"conflict_type={self.conflict_type.name}, "
            f"similarity_score={self.similarity_score}, "
            f"confidence={self.confidence}, "
            f"affected_fields={self.affected_fields!r})"
        )


__all__ = [
    "AUTO_RESOLVABLE_TYPES",
    "HUMAN_APPROVAL_REQUIRED_TYPES",
    "ModelGeometricConflictDetails",
]
