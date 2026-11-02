# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Champion decision computed from an experiment verdict (OMN-22001)."""

from typing import Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_champion_decision import EnumChampionDecision
from omnibase_core.enums.enum_retrospective_verdict import EnumRetrospectiveVerdict
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelChampionDecision(BaseModel):
    """PROMOTE, RETAIN or REJECT, computed from a verdict and kept apart from it.

    The verdict model carries no decision. A PROMOTE needs a PASS verdict.

    Attributes:
        experiment_id: The experiment.
        decision: The champion decision.
        verdict: The verdict the decision was computed from.
        evaluator_version: Evaluator version that computed the verdict.
        input_hash: Hash of the evidence snapshot behind the verdict.
        decided_at: When the decision was computed.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    experiment_id: UUID
    decision: EnumChampionDecision
    verdict: EnumRetrospectiveVerdict
    evaluator_version: ModelSemVer
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    decided_at: AwareDatetime

    @model_validator(mode="after")
    def _promote_needs_a_pass(self) -> Self:
        if (
            self.decision is EnumChampionDecision.PROMOTE
            and self.verdict is not EnumRetrospectiveVerdict.PASS
        ):
            raise ValueError("a PROMOTE decision needs a PASS verdict")
        return self
