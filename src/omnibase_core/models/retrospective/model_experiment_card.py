# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Experiment card, populated automatically for one candidate slot (OMN-21627)."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_experiment_approval_state import (
    EnumExperimentApprovalState,
)
from omnibase_core.enums.enum_experiment_slot import EnumExperimentSlot
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelExperimentCard(BaseModel):
    """One proposed or running experiment. Unknown values stay ``None``.

    Attributes:
        slot: Origin slot.
        experiment_id: The experiment.
        hypothesis: The hypothesis under test.
        owner_role: Proposed or confirmed owner, as a role.
        skill_name: The skill under test.
        skill_version: Its version.
        eligible_cohort: The eligible cohort, in words.
        primary_endpoint: The primary endpoint, in words.
        guardrails: Guardrails, in words.
        baseline: Baseline description, once measured.
        observation_cutoff: Observation cutoff, once agreed.
        approval_state: Whether the card has authority to run.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    slot: EnumExperimentSlot
    experiment_id: UUID
    hypothesis: str = Field(min_length=1)
    owner_role: str | None = None
    skill_name: str = Field(min_length=1)
    skill_version: ModelSemVer | None = None
    eligible_cohort: str = Field(min_length=1)
    primary_endpoint: str = Field(min_length=1)
    guardrails: tuple[str, ...] = ()
    baseline: str | None = None
    observation_cutoff: AwareDatetime | None = None
    approval_state: EnumExperimentApprovalState = EnumExperimentApprovalState.PROPOSED
