# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Confirmation that a run state was written to its projection (OMN-21627)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_retrospective_run_phase import EnumRetrospectiveRunPhase


class ModelRetrospectiveRunProjected(BaseModel):
    """One projected revision of one run, keyed by run and revision.

    Attributes:
        run_id: Identity of the run.
        correlation_id: Correlation identity of the run.
        phase: The projected phase.
        revision: The projected revision.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    correlation_id: UUID
    phase: EnumRetrospectiveRunPhase
    revision: int = Field(ge=1)
