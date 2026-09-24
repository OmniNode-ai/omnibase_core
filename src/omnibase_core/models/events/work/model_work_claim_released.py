# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Claim-released work event (OMN-16177)."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import Field, model_validator

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
    claim_event_id: uuid.UUID = Field(
        ...,
        description="event_id of the work.claim.requested this releases.",
    )

    @model_validator(mode="after")
    def _does_not_release_itself(self) -> ModelWorkClaimReleased:
        if self.claim_event_id == self.event_id:
            raise ValueError("a release cannot name itself as the claim it releases")
        return self
