# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A question reference the work-ledger fold refused (OMN-19620, plan T17)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_invalid_question_ref_reason import (
    EnumInvalidQuestionRefReason,
)
from omnibase_core.models.events.work.model_work_operator_consent_recorded import (
    ModelWorkOperatorConsentRecorded,
)
from omnibase_core.models.events.work.model_work_question_withdrawn import (
    ModelWorkQuestionWithdrawn,
)
from omnibase_core.models.events.work.model_work_ruling_recorded import (
    ModelWorkRulingRecorded,
)

__all__ = ["ModelInvalidQuestionRef"]


class ModelInvalidQuestionRef(BaseModel):
    """An answer or withdrawal reference that answers or withdraws nothing, and why."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    referrer: (
        ModelWorkRulingRecorded
        | ModelWorkOperatorConsentRecorded
        | ModelWorkQuestionWithdrawn
    ) = Field(
        ...,
        discriminator="kind",
        description="The ruling, consent or withdrawal holding the reference.",
    )
    target: uuid.UUID = Field(..., description="The event_id it names.")
    reason: EnumInvalidQuestionRefReason = Field(..., description="Why it was refused.")
