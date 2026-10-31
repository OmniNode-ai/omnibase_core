# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Orchestrator request to the digest effect for one projected run (OMN-21627)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelRetrospectiveDigestRequest(BaseModel):
    """Publish the digest of one evaluated, projected run revision.

    Attributes:
        run_id: Identity of the run.
        correlation_id: Correlation identity of the run.
        revision: The projected revision the digest reports.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    correlation_id: UUID
    revision: int = Field(ge=1)
