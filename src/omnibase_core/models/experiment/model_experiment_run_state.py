# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Run state of one experiment in the ab-compare reducer's lifecycle FSM (OMN-22001)."""

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_experiment_lifecycle_state import (
    EnumExperimentLifecycleState,
)
from omnibase_core.enums.enum_experiment_subject_kind import EnumExperimentSubjectKind
from omnibase_core.models.experiment.model_champion_decision import (
    ModelChampionDecision,
)
from omnibase_core.models.experiment.model_experiment_refusal import (
    ModelExperimentRefusal,
)
from omnibase_core.models.experiment.model_experiment_verdict import (
    ModelExperimentVerdict,
)

_STATE = EnumExperimentLifecycleState


class ModelExperimentRunState(BaseModel):
    """The state of one experiment after the reducer folds one event.

    One FSM serves every subject kind: a subject whose manifest declares no
    calibration or validation phase sets ``subject_requires_calibration`` False and
    passes those states through guarded transitions.

    Attributes:
        experiment_id: The experiment.
        correlation_id: Correlation identity of the run.
        subject_kind: What the experiment is about.
        state: Where the experiment is in the lifecycle.
        revision: Rises with every fold and is never reused.
        subject_requires_calibration: Whether the subject has calibration and validation.
        rule_sha: The manifest's rule hash, present from SEALED on.
        verdict: The verdict, present at EVALUATED and DECIDED.
        decision: The champion decision, present only at DECIDED.
        refusal: The refusal, present only at REFUSED and VOID.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    experiment_id: UUID
    correlation_id: UUID
    subject_kind: EnumExperimentSubjectKind
    state: EnumExperimentLifecycleState
    revision: int = Field(ge=1)
    subject_requires_calibration: bool = False
    rule_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    verdict: ModelExperimentVerdict | None = None
    decision: ModelChampionDecision | None = None
    refusal: ModelExperimentRefusal | None = None

    @model_validator(mode="after")
    def _fields_match_the_state(self) -> Self:
        if self.state.is_sealed_or_later and self.rule_sha is None:
            raise ValueError(f"state {self.state.value} needs the manifest rule_sha")
        if self.state in (_STATE.EVALUATED, _STATE.DECIDED) and self.verdict is None:
            raise ValueError(f"state {self.state.value} needs a verdict")
        if self.state is _STATE.DECIDED and self.decision is None:
            raise ValueError("state decided needs a champion decision")
        if self.state is not _STATE.DECIDED and self.decision is not None:
            raise ValueError("a champion decision exists only at state decided")
        if self.state is _STATE.REFUSED and self.refusal is None:
            raise ValueError("state refused needs a refusal")
        if self.refusal is not None and self.state not in (_STATE.REFUSED, _STATE.VOID):
            raise ValueError("a refusal exists only at state refused or void")
        for part in (self.verdict, self.decision, self.refusal):
            if part is not None and part.experiment_id != self.experiment_id:
                raise ValueError(
                    "verdict, decision and refusal must name this experiment"
                )
        return self
