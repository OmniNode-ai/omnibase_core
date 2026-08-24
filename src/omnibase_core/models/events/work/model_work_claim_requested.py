# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Claim-requested work event (OMN-16177)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_work_event_base import ModelWorkEventBase

__all__ = ["ModelWorkClaimRequested"]


class ModelWorkClaimRequested(ModelWorkEventBase):
    """A claimant asks to own a ticket.

    ``ticket_id`` is narrowed to required: it is this kind's partition key, and
    a null key cannot arbitrate.
    """

    kind: Literal[EnumWorkEventKind.CLAIM_REQUESTED] = Field(
        default=EnumWorkEventKind.CLAIM_REQUESTED, frozen=True
    )
    ticket_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Ticket being claimed. Required — this is the partition key.",
    )
