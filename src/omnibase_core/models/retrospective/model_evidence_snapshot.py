# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Immutable evidence snapshot the collector hands to the evaluator (OMN-21627)."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from omnibase_core.models.retrospective.model_experiment_evidence_record import (
    ModelExperimentEvidenceRecord,
)
from omnibase_core.models.retrospective.model_success_contract import (
    ModelSuccessContract,
)


class ModelEvidenceSnapshot(BaseModel):
    """Every record and contract of one run, frozen at the cutoff and watermark.

    Replaying the same snapshot through the same evaluator version must give the
    same verdicts and the same explanation.

    Attributes:
        run_id: Identity of the run.
        correlation_id: Correlation identity of the run.
        cohort_cutoff: Cutoff the snapshot was frozen at.
        ingestion_watermark: Ingestion watermark at freeze time.
        input_hash: SHA-256 of the canonical snapshot content (64 lowercase hex).
        contracts: The frozen success contract of every experiment in the run.
        records: Every deduplicated evidence record inside the window.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    correlation_id: UUID
    cohort_cutoff: AwareDatetime
    ingestion_watermark: AwareDatetime
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    contracts: tuple[ModelSuccessContract, ...] = ()
    records: tuple[ModelExperimentEvidenceRecord, ...] = ()
