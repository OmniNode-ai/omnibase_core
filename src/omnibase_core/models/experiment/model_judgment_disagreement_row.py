# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One row recording that a judge disagreed with the rule (OMN-22001)."""

from typing import Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_retrospective_verdict import EnumRetrospectiveVerdict
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.experiment.model_judgment_record import ModelJudgmentRecord


class ModelJudgmentDisagreementRow(BaseModel):
    """A judgment whose answer differs from the deterministic rule result.

    Attributes:
        judgment_id: The judgment that disagreed.
        experiment_id: The experiment judged.
        model_name: Name of the judge model.
        rubric_name: Name of the rubric.
        answer: The judge's answer.
        rule_result: The rule's result.
        recorded_at: When the row was recorded.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    judgment_id: UUID
    experiment_id: UUID
    model_name: str = Field(min_length=1)
    rubric_name: str = Field(min_length=1)
    answer: EnumRetrospectiveVerdict
    rule_result: EnumRetrospectiveVerdict
    recorded_at: AwareDatetime

    @model_validator(mode="after")
    def _answer_and_rule_disagree(self) -> Self:
        if self.answer is self.rule_result:
            raise ValueError(
                "a disagreement row needs an answer that differs from the rule"
            )
        return self

    @classmethod
    def from_judgment(
        cls, judgment: ModelJudgmentRecord, *, recorded_at: AwareDatetime
    ) -> Self:
        """Build the row for a judgment, refusing one that agreed."""
        if not judgment.disagreement:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="the judgment does not disagree with the rule result",
            )
        return cls(
            judgment_id=judgment.judgment_id,
            experiment_id=judgment.experiment_id,
            model_name=judgment.model_name,
            rubric_name=judgment.rubric_name,
            answer=judgment.answer,
            rule_result=judgment.rule_result,
            recorded_at=recorded_at,
        )
