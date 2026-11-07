# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One failing admission rule of a ticket create or update (OMN-22850)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelTicketCreationFinding(BaseModel):
    """One refusal: a stable code, the payload field, what is wrong and what to do."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    code: str = Field(
        description="The rule id of the contract row that produced this finding"
    )
    field: str = Field(description="The payload field the finding is about")
    reason: str = Field(description="What is wrong")
    fix: str = Field(description="What to do about it")
