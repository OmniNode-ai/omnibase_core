# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed evidence a skill seam records for one eligible unit (OMN-21627)."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_evidence_unit_outcome import EnumEvidenceUnitOutcome
from omnibase_core.enums.enum_experiment_slot import EnumExperimentSlot
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelExperimentEvidenceRecord(BaseModel):
    """One eligible unit's evidence, with provenance.

    Attributes:
        record_id: Stable event identity, used to deduplicate and to reject conflicts.
        slot: Origin slot of the experiment.
        experiment_id: The experiment the unit belongs to.
        unit_ref: Reference to the eligible unit.
        outcome: What is known about the unit; unknown stays unknown.
        source_ref: The stored result the record was derived from.
        source_hash: SHA-256 of that result (64 lowercase hex).
        assessor_version: Version of the seam or assessor that classified the unit.
        recorded_at: When the seam recorded it.
        correlation_id: Correlation identity of the skill run.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    record_id: UUID
    slot: EnumExperimentSlot
    experiment_id: UUID
    unit_ref: str = Field(min_length=1)
    outcome: EnumEvidenceUnitOutcome
    source_ref: str = Field(min_length=1)
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    assessor_version: ModelSemVer
    recorded_at: AwareDatetime
    correlation_id: UUID
