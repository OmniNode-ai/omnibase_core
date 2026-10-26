# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One ruling's or consent's derived state (OMN-21107, TA.5)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.events.work.model_work_operator_consent_recorded import (
    ModelWorkOperatorConsentRecorded,
)
from omnibase_core.models.events.work.model_work_ruling_recorded import (
    ModelWorkRulingRecorded,
)

__all__ = ["ModelRulingState"]


class ModelRulingState(BaseModel):
    """A ruling or consent, whether it is still open, and every event naming it.

    A ruling or consent is open unless at least one valid supersedes link
    targets it. Amends, extends and corrects never close: the sources are
    recorded here for display, and the ruling stays as it was.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    ruling: ModelWorkRulingRecorded | ModelWorkOperatorConsentRecorded = Field(
        ...,
        discriminator="kind",
        description="The ruling or consent event.",
    )
    is_open: bool = Field(
        ...,
        description="False once a valid supersedes link targets it, else True.",
    )
    superseded_by: tuple[uuid.UUID, ...] = Field(
        default=(),
        description="Event_ids superseding it, sorted by str.",
    )
    amended_by: tuple[uuid.UUID, ...] = Field(
        default=(),
        description="Event_ids amending it, sorted by str.",
    )
    extended_by: tuple[uuid.UUID, ...] = Field(
        default=(),
        description="Event_ids extending it, sorted by str.",
    )
    corrected_by: tuple[uuid.UUID, ...] = Field(
        default=(),
        description="Event_ids of corrections naming it, sorted by str.",
    )
