# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Hold-placed work event (OMN-16177, typed work ledger).

A hold is in force from the moment it is recorded until a
``work.hold.released`` names its ``event_id``. Nothing else lifts it: not a
later prose row, not the passage of time. A surface lease carries
``expires_at``, and an expired lease that was never released stays in force,
marked expired, until a typed reap release names it.
"""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field, field_serializer, model_validator

from omnibase_core.enums.enum_hold_block import EnumHoldBlock
from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_hold_scope import ModelHoldScope
from omnibase_core.models.events.work.model_recipients import ModelRecipients
from omnibase_core.models.events.work.model_work_event_base import ModelWorkEventBase

__all__ = ["ModelWorkHoldPlaced"]

UNTIL_TEXT_MAX_LENGTH = 500


class ModelWorkHoldPlaced(ModelWorkEventBase):
    """A typed hold on PRs, repos, surfaces or lanes."""

    kind: Literal[EnumWorkEventKind.HOLD_PLACED] = Field(
        default=EnumWorkEventKind.HOLD_PLACED, frozen=True
    )
    scope: ModelHoldScope = Field(..., description="What the hold covers.")
    blocks: frozenset[EnumHoldBlock] = Field(
        ...,
        min_length=1,
        description="Which actions the hold stops. At least one.",
    )
    runtime_only: bool = Field(
        default=False,
        description=(
            "When True, the hold applies only to runtime-affecting PRs in scope "
            "(a runtime-merge pause)."
        ),
    )
    addressed_to: ModelRecipients | None = Field(
        default=None,
        description="Who is told about the hold. It binds its scope either way.",
    )
    expires_at: AwareDatetime | None = Field(
        default=None,
        description=(
            "Lease expiry. Set only on a surface lease (scope.surfaces non-empty). "
            "Expiry marks the lease EXPIRED-UNRELEASED; it does not release it."
        ),
    )
    until_text: str | None = Field(
        default=None,
        max_length=UNTIL_TEXT_MAX_LENGTH,
        description="Human-readable lift condition. Display only; never read by a checker.",
    )

    @model_validator(mode="after")
    def _expiry_only_on_a_surface_lease(self) -> ModelWorkHoldPlaced:
        if self.expires_at is None:
            return self
        if not self.scope.surfaces:
            raise ValueError(
                "expires_at is set only on a surface lease; this hold's scope "
                "names no surface"
            )
        if self.expires_at <= self.emitted_at:
            raise ValueError("expires_at must be later than emitted_at")
        return self

    @field_serializer("blocks")
    def _serialize_blocks_sorted(
        self, value: frozenset[EnumHoldBlock]
    ) -> list[EnumHoldBlock]:
        return sorted(value, key=lambda block: block.value)
