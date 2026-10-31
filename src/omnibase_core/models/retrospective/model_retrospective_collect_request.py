# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Orchestrator request to the collector effect for one run (OMN-21627)."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict


class ModelRetrospectiveCollectRequest(BaseModel):
    """Collect the evidence of one run's cohort window from the approved sources.

    Attributes:
        run_id: Identity of the run.
        correlation_id: Correlation identity of the run.
        cohort_start: Start of the cohort window.
        cohort_cutoff: Cutoff of the cohort window.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    correlation_id: UUID
    cohort_start: AwareDatetime
    cohort_cutoff: AwareDatetime
