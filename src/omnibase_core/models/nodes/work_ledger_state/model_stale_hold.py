# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A stale hold: open-ended, never released, older than 14 days (OMN-21947, plan L3)."""

from __future__ import annotations

from datetime import timedelta

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.work_ledger_state.model_hold_in_force import (
    ModelHoldInForce,
)

__all__ = ["ModelStaleHold"]


class ModelStaleHold(BaseModel):
    """A hold the readers list under the stale heading, with its age.

    Settled operator rule: an open-ended hold with no release that is older than 14
    days is stale. It is reported, not enforced.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    hold: ModelHoldInForce = Field(..., description="The hold as the fold kept it.")
    age: timedelta = Field(
        ..., description="The as-of time minus the hold's emitted_at."
    )
