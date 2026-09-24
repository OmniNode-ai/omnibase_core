# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Hold-released work event (OMN-16177, typed work ledger).

The only thing that lifts a hold. It names the hold by ``event_id``; any lane
may record it, and the releasing actor is on the event. Whether the named hold
exists, and whether a surface outcome is required because that hold carries
surfaces, is checked by the fold, which sees both events. This model checks
only what a release can get wrong on its own.
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import Field, model_validator

from omnibase_core.enums.enum_surface_result import EnumSurfaceResult
from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_hold_scope import ModelHoldScope
from omnibase_core.models.events.work.model_work_event_base import ModelWorkEventBase

__all__ = ["ModelWorkHoldReleased"]


class ModelWorkHoldReleased(ModelWorkEventBase):
    """Releases one hold, wholly or in part."""

    kind: Literal[EnumWorkEventKind.HOLD_RELEASED] = Field(
        default=EnumWorkEventKind.HOLD_RELEASED, frozen=True
    )
    releases: uuid.UUID = Field(
        ..., description="event_id of the work.hold.placed this releases."
    )
    partial_scope: ModelHoldScope | None = Field(
        default=None,
        description="The part of the hold's scope released. None releases the whole hold.",
    )
    reap: bool = Field(
        default=False,
        description=(
            "True only when releasing an expired surface lease its holder never "
            "released. A reap releases the whole lease and reports its surface outcome."
        ),
    )
    surface_result: EnumSurfaceResult | None = Field(
        default=None,
        description="How the work on the surface ended. Paired with surface_restored.",
    )
    surface_restored: bool | None = Field(
        default=None,
        description="Whether the surface was restored. Paired with surface_result.",
    )

    @model_validator(mode="after")
    def _release_is_coherent(self) -> ModelWorkHoldReleased:
        if self.releases == self.event_id:
            raise ValueError("a release cannot name itself as the hold it releases")
        if (self.surface_result is None) != (self.surface_restored is None):
            raise ValueError(
                "surface_result and surface_restored are recorded together or not at all"
            )
        if self.reap:
            if self.partial_scope is not None:
                raise ValueError(
                    "a reap releases the whole expired lease; partial_scope must be None"
                )
            if self.surface_result is None:
                raise ValueError(
                    "a reap releases a surface lease and must record surface_result "
                    "and surface_restored"
                )
        return self
