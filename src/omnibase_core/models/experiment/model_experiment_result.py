# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shared Experiment Result Contract — canonical experiment telemetry (OMN-13613).

``ModelExperimentResult`` is the single result schema emitted by every Phase-3
experiment orchestrator of the SEA→canonical migration (epic OMN-13604):

* ``node_entropy_experiment_orchestrator`` (OMN-13614)
* ``node_model_eval_orchestrator`` (OMN-13615)
* ``node_regression_test_orchestrator`` (OMN-13616)

It is homed in ``omnibase_core`` (shared models) because those three nodes plus
``omnimarket`` import it — ``>= 2`` repos consume it, so it belongs in core
(see ``feedback_models_in_core_not_market.md``). No experiment node may invent
its own result schema; they all import from here.

Every field is strongly typed: identifiers are ``UUID``, lifecycle/classification
fields are enums, and ``score`` / ``cost`` / ``evidence_ref`` are frozen typed
value objects rather than bare scalars or ``str``. The model is frozen.

.. versionadded:: OMN-13613
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_experiment_status import EnumExperimentStatus
from omnibase_core.enums.enum_experiment_type import EnumExperimentType
from omnibase_core.models.experiment.model_experiment_cost import ModelExperimentCost
from omnibase_core.models.experiment.model_experiment_evidence_ref import (
    ModelExperimentEvidenceRef,
)
from omnibase_core.models.experiment.model_experiment_score import ModelExperimentScore

__all__ = ["ModelExperimentResult"]


class ModelExperimentResult(BaseModel):
    """Canonical result emitted by every Phase-3 experiment orchestrator.

    All three experiment nodes (OMN-13614 / OMN-13615 / OMN-13616) plus
    ``omnimarket`` produce/consume this exact shape — one result model, not
    three. Every field is strongly typed and the model is frozen.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    experiment_id: UUID = Field(
        ...,
        description="Unique identifier for this experiment.",
    )
    experiment_type: EnumExperimentType = Field(
        ...,
        description="Which canonical experiment orchestrator produced the result.",
    )
    run_id: UUID = Field(
        ...,
        description="Identifier of the specific run that produced this result.",
    )
    correlation_id: UUID = Field(
        ...,
        description="Correlation identifier linking events across the run.",
    )
    runtime_identity: str = Field(
        ...,
        min_length=1,
        description=(
            "Runtime lane/service identity that executed the experiment "
            "(e.g. 'stability-test/runtime-local')."
        ),
    )
    score: ModelExperimentScore = Field(
        ...,
        description="Typed numeric score produced by the experiment.",
    )
    cost: ModelExperimentCost = Field(
        ...,
        description="Typed dollar cost of the experiment.",
    )
    status: EnumExperimentStatus = Field(
        ...,
        description="Lifecycle/terminal status of the experiment run.",
    )
    evidence_ref: ModelExperimentEvidenceRef = Field(
        ...,
        description="Typed reference to the durable evidence backing the result.",
    )
