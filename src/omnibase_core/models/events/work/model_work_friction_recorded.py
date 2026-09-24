# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Friction-recorded work event (OMN-16177, typed work ledger).

Process friction always names the ticket that owns its fix and what it cost,
and says whether that cost was measured or estimated. A result that cites
friction names these events by ``event_id`` in ``friction_refs``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_cost_basis import EnumCostBasis
from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_work_event_base import ModelWorkEventBase

__all__ = ["FRICTION_TICKET_PATTERN", "ModelWorkFrictionRecorded"]

FRICTION_TICKET_PATTERN = r"^OMN-\d+$"


class ModelWorkFrictionRecorded(ModelWorkEventBase):
    """One friction item, with its ticket and its cost."""

    kind: Literal[EnumWorkEventKind.FRICTION_RECORDED] = Field(
        default=EnumWorkEventKind.FRICTION_RECORDED, frozen=True
    )
    ticket_id: str = Field(
        ...,
        pattern=FRICTION_TICKET_PATTERN,
        max_length=64,
        description="Ticket that owns the fix. Required, an OMN id.",
    )
    cost_lane_hours: Decimal = Field(
        ...,
        ge=0,
        allow_inf_nan=False,
        description="What the friction cost, in lane-hours.",
    )
    cost_basis: EnumCostBasis = Field(
        ..., description="Whether cost_lane_hours was measured or estimated."
    )
