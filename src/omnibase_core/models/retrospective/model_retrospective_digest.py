# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The one concise asynchronous digest of a retrospective run (OMN-21627)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.retrospective.model_experiment_card import ModelExperimentCard
from omnibase_core.models.retrospective.model_experiment_verdict import (
    ModelExperimentVerdict,
)


class ModelRetrospectiveDigest(BaseModel):
    """What changed, what the evidence supports and only the decisions a person must make.

    A slot may hold no new card: the digest never invents changes to fill a quota.

    Attributes:
        run_id: Identity of the run.
        correlation_id: Correlation identity of the run.
        revision: The projected run revision the digest reports.
        verdicts: The reason-coded verdict of each experiment.
        candidate_cards: At most three candidate cards, one per origin slot.
        decisions_needed: Only the decisions that need a person.
        degraded: True when coverage or a source was missing.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    correlation_id: UUID
    revision: int = Field(ge=1)
    verdicts: tuple[ModelExperimentVerdict, ...] = ()
    candidate_cards: tuple[ModelExperimentCard, ...] = Field(default=(), max_length=3)
    decisions_needed: tuple[str, ...] = ()
    degraded: bool
