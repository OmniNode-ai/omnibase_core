# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Command that opens one bounded retrospective review run (OMN-21627)."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelRetrospectiveRunOpen(BaseModel):
    """Open one review run over one cohort window.

    Attributes:
        run_id: Identity of the run.
        correlation_id: Correlation identity carried through every crossing.
        idempotency_key: Review week plus relevant versions; a second open with the
            same key is the same run, never a duplicate report.
        cohort_start: Start of the cohort window.
        cohort_cutoff: Cutoff of the cohort window; events after it are excluded.
        configuration_version: Version of the approved configuration (cadence,
            sources, retention, recipients, authority boundaries).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    correlation_id: UUID
    idempotency_key: str = Field(min_length=1)
    cohort_start: AwareDatetime
    cohort_cutoff: AwareDatetime
    configuration_version: ModelSemVer
