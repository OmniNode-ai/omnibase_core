# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Evaluation result model — the output of the ScoringReducer.

The EvaluationResult is the pure output of evaluating an EvidenceBundle
against an ObjectiveSpec. It is deterministic: same inputs always produce
the same result.

Part of the objective functions and reward architecture (OMN-2537).
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.objective.model_score_vector import ModelScoreVector

__all__ = ["ModelEvaluationResult"]


class ModelEvaluationResult(BaseModel):
    """The result of evaluating an EvidenceBundle against an ObjectiveSpec.

    This is the output of the ScoringReducer (a COMPUTE node — pure,
    deterministic, no I/O). It captures whether the run passed all gates,
    the score vector, any gate failures, and attribution references.

    Invariants:
    - If passed=False, score_vector MUST equal ModelScoreVector.zero().
    - If passed=True, failures MUST be empty.
    - If failures is non-empty, passed MUST be False.

    Attributes:
        passed: True if all hard gates passed; False if any gate failed.
        score_vector: The multi-dimensional score vector for this run.
        failures: Gate IDs that failed (empty if passed=True).
        attribution_refs: Evidence item IDs traceable to specific score components.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    passed: bool = Field(
        description="True if all hard gates passed; False if any gate failed"
    )
    score_vector: ModelScoreVector = Field(
        description=(
            "Multi-dimensional score vector. Must be ModelScoreVector.zero() "
            "when passed=False."
        )
    )
    failures: list[str] = Field(  # string-id-ok: gate IDs that failed
        description="Gate IDs that failed. Empty when passed=True."
    )
    attribution_refs: list[str] = Field(  # string-ref-ok: evidence item IDs
        description=(
            "Evidence item IDs traceable to specific score components. "
            "Empty when passed=False."
        )
    )

    @model_validator(mode="after")
    def validate_consistency(self) -> "ModelEvaluationResult":
        """Enforce consistency invariants between passed, score_vector, and failures.

        Invariants enforced:
        1. If passed=False: score_vector must equal ModelScoreVector.zero()
        2. If passed=True: failures must be empty
        3. If failures non-empty: passed must be False

        Returns:
            Self after validation.

        Raises:
            ValueError: If any invariant is violated.
        """
        zero = ModelScoreVector.zero()

        if not self.passed:
            # Gate failure: score vector must be zero
            if self.score_vector != zero:
                raise ValueError(
                    "When passed=False, score_vector must equal ModelScoreVector.zero(). "
                    f"Got: {self.score_vector}"
                )
        # All gates passed: no failures allowed
        elif self.failures:
            raise ValueError(
                f"When passed=True, failures must be empty. Got: {self.failures}"
            )

        # Failures non-empty implies passed=False
        if self.failures and self.passed:
            raise ValueError(
                f"failures list is non-empty but passed=True: {self.failures}"
            )

        return self
