# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ObjectiveSpec model — the core objective contract.

Objectives are first-class contracts. They are not configuration, not
heuristics. Every ObjectiveSpec is versioned, declarative, replayable,
explainable, bounded, and tamper-evident.

Part of the objective functions and reward architecture (OMN-2537).
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.objective.model_gate_spec import ModelGateSpec
from omnibase_core.models.objective.model_score_range import ModelScoreRange
from omnibase_core.models.objective.model_shaped_term_spec import ModelShapedTermSpec

__all__ = ["ModelObjectiveSpec"]

# Valid ScoreVector field names for lexicographic_priority validation
_SCORE_VECTOR_FIELDS = frozenset(
    {"correctness", "safety", "cost", "latency", "maintainability", "human_time"}
)


class ModelObjectiveSpec(BaseModel):
    """Objective specification contract.

    An ObjectiveSpec is the complete, versioned definition of what success
    means for a class of runs. It declares gates (hard pass/fail checks),
    shaped terms (optimization directions), score bounds, and lexicographic
    priority for multi-objective selection.

    Invariants:
    - Every objective has a unique objective_id and version.
    - Score changes require a version bump.
    - The lexicographic_priority list must reference valid ScoreVector fields.
    - Changing the priority ordering requires a version bump.
    - The spec is fingerprinted and stored with each EvaluationResult.

    Attributes:
        objective_id: Unique identifier for this objective.
        version: Semantic version of this objective spec.
        gates: Hard gate checks evaluated before any shaped terms.
        shaped_terms: Reward shaping terms applied only when all gates pass.
        score_range: Declared min/max bounds for the overall score output.
        lexicographic_priority: ScoreVector field names in priority order,
            highest priority first (e.g., ["correctness", "safety", "cost"]).
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    objective_id: str = Field(  # string-id-ok: domain-scoped objective identifier
        description="Unique identifier for this objective (e.g., 'omniclaude.task.v1')"
    )
    version: str = Field(  # string-version-ok: semantic version for replay integrity
        description="Semantic version of this objective spec (e.g., '1.0.0')"
    )
    gates: list[ModelGateSpec] = Field(
        description="Hard gate checks evaluated before any shaped reward terms"
    )
    shaped_terms: list[ModelShapedTermSpec] = Field(
        description="Shaped reward terms applied only when all gates pass"
    )
    score_range: ModelScoreRange = Field(
        description="Declared min/max bounds for the overall score output"
    )
    lexicographic_priority: list[str] = Field(
        description=(
            "ScoreVector field names in priority order, highest priority first. "
            "Must be valid ScoreVector fields. Changing this ordering requires a version bump."
        )
    )

    @model_validator(mode="after")
    def validate_lexicographic_priority(self) -> "ModelObjectiveSpec":
        """Validate that all lexicographic_priority entries are valid ScoreVector fields.

        Returns:
            Self after validation.

        Raises:
            ValueError: If any priority entry is not a valid ScoreVector field name.
        """
        invalid = [
            f for f in self.lexicographic_priority if f not in _SCORE_VECTOR_FIELDS
        ]
        if invalid:
            raise ValueError(
                f"lexicographic_priority contains invalid ScoreVector field names: {invalid}. "
                f"Valid fields: {sorted(_SCORE_VECTOR_FIELDS)}"
            )
        return self
