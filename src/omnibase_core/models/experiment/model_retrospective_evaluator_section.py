# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Evaluator-section input the retrospective render takes (OMN-22001)."""

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.experiment.model_champion_decision import (
    ModelChampionDecision,
)
from omnibase_core.models.experiment.model_evidence_cost import ModelEvidenceCost
from omnibase_core.models.experiment.model_experiment_refusal import (
    ModelExperimentRefusal,
)
from omnibase_core.models.experiment.model_experiment_verdict import (
    ModelExperimentVerdict,
)
from omnibase_core.models.experiment.model_judgment_disagreement_row import (
    ModelJudgmentDisagreementRow,
)
from omnibase_core.models.experiment.model_judgment_record import ModelJudgmentRecord
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelRetrospectiveEvaluatorSection(BaseModel):
    """Everything the evaluator section of the retrospective render needs, typed.

    Attributes:
        run_id: Identity of the run.
        correlation_id: Correlation identity of the run.
        revision: The projected run revision the section reports.
        evaluator_version: Evaluator version that computed the verdicts.
        input_hash: Hash of the evidence snapshot behind the verdicts.
        verdicts: The reason-coded verdict of each experiment.
        decisions: Champion decisions, each for an experiment that has a verdict.
        refusals: Operational refusals of the loop.
        judgments: Judge records.
        disagreements: Rows for judgments that disagreed with the rule.
        cost: Cost of the run, measured or unknown.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    correlation_id: UUID
    revision: int = Field(ge=1)
    evaluator_version: ModelSemVer
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    verdicts: tuple[ModelExperimentVerdict, ...] = ()
    decisions: tuple[ModelChampionDecision, ...] = ()
    refusals: tuple[ModelExperimentRefusal, ...] = ()
    judgments: tuple[ModelJudgmentRecord, ...] = ()
    disagreements: tuple[ModelJudgmentDisagreementRow, ...] = ()
    cost: ModelEvidenceCost = Field(default_factory=ModelEvidenceCost)

    @model_validator(mode="after")
    def _parts_belong_to_the_run(self) -> Self:
        judged = {v.experiment_id for v in self.verdicts}
        for decision in self.decisions:
            if decision.experiment_id not in judged:
                raise ValueError("a decision needs a verdict for the same experiment")
        flagged = {j.judgment_id for j in self.judgments if j.disagreement}
        for row in self.disagreements:
            if row.judgment_id not in flagged:
                raise ValueError("a disagreement row needs a disagreeing judgment")
        return self
