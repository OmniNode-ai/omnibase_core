# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Reducer state of one retrospective run, as projected (OMN-21627)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_retrospective_run_phase import EnumRetrospectiveRunPhase
from omnibase_core.models.retrospective.model_experiment_verdict import (
    ModelExperimentVerdict,
)


class ModelRetrospectiveRunState(BaseModel):
    """The canonical state of a run after the reducer folds one event.

    Late evidence creates a new revision, never a silent overwrite.

    Attributes:
        run_id: Identity of the run.
        correlation_id: Correlation identity of the run.
        phase: Where the run is in its state machine.
        revision: Rises with every fold and is never reused for a run.
        input_hash: Hash of the snapshot behind the verdicts, once collected.
        verdicts: The verdicts, once evaluated.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    correlation_id: UUID
    phase: EnumRetrospectiveRunPhase
    revision: int = Field(ge=1)
    input_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    verdicts: tuple[ModelExperimentVerdict, ...] = ()
