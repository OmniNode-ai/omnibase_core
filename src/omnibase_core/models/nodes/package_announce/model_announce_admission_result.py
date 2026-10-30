# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result of admitting one announcement (OMN-21589)."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_announce_refusal_reason import EnumAnnounceRefusalReason


class ModelAnnounceAdmissionResult(BaseModel):
    """The typed reason admission refused, or no reason when it admitted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    refusal_reason: EnumAnnounceRefusalReason | None = None
