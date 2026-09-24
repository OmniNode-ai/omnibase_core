# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Claim-requested work event (OMN-16177)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_serializer

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_pr_key import ModelPrKey
from omnibase_core.models.events.work.model_work_event_base import (
    SUMMARY_MAX_LENGTH,
    ModelWorkEventBase,
)

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
    prs: frozenset[ModelPrKey] = Field(
        default_factory=frozenset,
        description="Pull requests the claim covers, keyed by repo and number.",
    )
    scope_text: str | None = Field(
        default=None,
        min_length=1,
        max_length=SUMMARY_MAX_LENGTH,
        description="What the claim covers and excludes, for humans. Never read by a checker.",
    )
    est_lane_hours: Decimal | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
        description="Estimated cost of the claimed work, in lane-hours (rule 4).",
    )
    displaces: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="What this work displaces (rule 4). Display only.",
    )
    consent_ref: uuid.UUID | None = Field(
        default=None,
        description="event_id of the work.consent.recorded that authorizes this work.",
    )

    @field_serializer("prs")
    def _serialize_prs_sorted(self, value: frozenset[ModelPrKey]) -> list[ModelPrKey]:
        return sorted(value, key=lambda key: (key.repo, key.number))
