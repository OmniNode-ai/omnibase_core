# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The evaluator's output for one run (OMN-21627)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.retrospective.model_experiment_verdict import (
    ModelExperimentVerdict,
)


class ModelRetrospectiveVerdictSet(BaseModel):
    """Every experiment verdict computed from one evidence snapshot.

    Attributes:
        run_id: Identity of the run.
        correlation_id: Correlation identity of the run.
        input_hash: Hash of the snapshot the verdicts were computed from.
        evaluator_version: Evaluator version.
        verdicts: One verdict per experiment in the snapshot.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    correlation_id: UUID
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluator_version: ModelSemVer
    verdicts: tuple[ModelExperimentVerdict, ...] = ()
