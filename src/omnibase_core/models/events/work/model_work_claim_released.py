# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Claim-released work event (OMN-16177)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_work_event_base import ModelWorkEventBase

__all__ = ["ModelWorkClaimReleased"]


class ModelWorkClaimReleased(ModelWorkEventBase):
    """A claimant gives up a ticket it previously claimed."""

    kind: Literal[EnumWorkEventKind.CLAIM_RELEASED] = Field(
        default=EnumWorkEventKind.CLAIM_RELEASED, frozen=True
    )
    ticket_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Ticket being released. Required — this is the partition key.",
    )
