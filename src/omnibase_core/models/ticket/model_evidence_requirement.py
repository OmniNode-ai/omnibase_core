# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelEvidenceRequirement — evidence requirement for ticket contract governance.

OMN-10064 / OMN-9582: Ported from onex_change_control.models.model_ticket_contract.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.ticket.enum_evidence_kind import EnumEvidenceKind

_MAX_STRING_LENGTH = 10000


class ModelEvidenceRequirement(BaseModel):
    """Evidence requirement in ticket contract.

    Declares what type of evidence must exist before a ticket can be marked Done.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: EnumEvidenceKind = Field(..., description="Type of evidence")
    description: str = Field(
        ...,
        description="What evidence must exist",
        max_length=_MAX_STRING_LENGTH,
    )
    command: str | None = Field(
        default=None,
        description="How to reproduce, if applicable",
        max_length=_MAX_STRING_LENGTH,
    )


__all__ = ["ModelEvidenceRequirement"]
