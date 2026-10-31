# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What an experiment skill hands to its seam after one run (OMN-21627)."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_experiment_slot import EnumExperimentSlot
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelExperimentSkillRunResult(BaseModel):
    """One run of an R1, R2 or R3 experiment skill, referenced by its stored result.

    Attributes:
        slot: Origin slot of the experiment.
        experiment_id: The experiment the run belongs to.
        skill_name: The skill that ran.
        skill_version: Its version.
        unit_ref: Reference to the eligible unit (a draft, a claim opportunity or an approval intent).
        result_ref: Where the full stored result lives.
        result_hash: SHA-256 of the full stored result (64 lowercase hex).
        completed_at: When the skill run ended.
        correlation_id: Correlation identity of the run.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    slot: EnumExperimentSlot
    experiment_id: UUID
    skill_name: str = Field(min_length=1)
    skill_version: ModelSemVer
    unit_ref: str = Field(min_length=1)
    result_ref: str = Field(min_length=1)
    result_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    completed_at: AwareDatetime
    correlation_id: UUID
