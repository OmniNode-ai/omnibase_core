# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A hold the work-ledger fold found still in force (OMN-19405, typed work ledger T4)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.events.work.model_work_hold_placed import ModelWorkHoldPlaced
from omnibase_core.models.events.work.model_work_hold_released import (
    ModelWorkHoldReleased,
)

__all__ = ["ModelHoldInForce"]


class ModelHoldInForce(BaseModel):
    """One hold in force, with the valid partial releases already applied to it.

    A partial release subtracts exactly its typed ``partial_scope`` from the
    hold. Those scopes are the hold's exemptions: a PR is held when the hold's
    scope covers it and no partial release's scope does.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    hold: ModelWorkHoldPlaced = Field(..., description="The hold as it was placed.")
    partial_releases: tuple[ModelWorkHoldReleased, ...] = Field(
        default=(),
        description="Valid partial releases naming this hold, sorted by event_id.",
    )
    expired_unreleased: bool = Field(
        default=False,
        description=(
            "True when the hold is a surface lease whose expires_at has passed at "
            "the fold's as_of. It still blocks until a typed reap release names it."
        ),
    )
