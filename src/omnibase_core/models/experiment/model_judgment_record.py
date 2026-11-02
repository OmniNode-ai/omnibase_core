# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A model judgment of one experiment, beside the deterministic rule result (OMN-22001)."""

from typing import Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_retrospective_verdict import EnumRetrospectiveVerdict
from omnibase_core.models.experiment.model_experiment_evidence_ref import (
    ModelExperimentEvidenceRef,
)
from omnibase_core.models.experiment.model_judgment_stored_input import (
    ModelJudgmentStoredInput,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelJudgmentRecord(BaseModel):
    """What a judge model answered, from which inputs, and whether the rule agreed.

    The record explains and never decides: the rule result stays the verdict, and a
    disagreement is recorded as a flag.

    Attributes:
        judgment_id: Identity of the judgment.
        experiment_id: The experiment judged.
        model_name: Name of the judge model.
        model_revision: Revision of the judge model.
        rubric_name: Name of the rubric.
        rubric_version: Version of the rubric.
        input_digest: SHA-256 digest of the inputs (64 lowercase hex).
        stored_inputs: The inputs, stored by value.
        cited_evidence: Evidence the judge cited.
        answer: The judge's answer.
        rule_result: The deterministic rule's result for the same inputs.
        disagreement: True exactly when the answer differs from the rule result.
        judged_at: When the judgment ran.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    judgment_id: UUID
    experiment_id: UUID
    model_name: str = Field(min_length=1)
    model_revision: str = Field(min_length=1)
    rubric_name: str = Field(min_length=1)
    rubric_version: ModelSemVer
    input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    stored_inputs: tuple[ModelJudgmentStoredInput, ...] = ()
    cited_evidence: tuple[ModelExperimentEvidenceRef, ...] = ()
    answer: EnumRetrospectiveVerdict
    rule_result: EnumRetrospectiveVerdict
    disagreement: bool
    judged_at: AwareDatetime

    @model_validator(mode="after")
    def _disagreement_follows_answer_and_rule(self) -> Self:
        differs = self.answer is not self.rule_result
        if self.disagreement != differs:
            raise ValueError(
                f"disagreement must be {differs} when answer is {self.answer.value} "
                f"and rule_result is {self.rule_result.value}"
            )
        return self
