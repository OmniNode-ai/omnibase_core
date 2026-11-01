# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One criterion statement of a ticket cited by a pull request (OMN-21823)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.ticket.enum_dod_check_type import EnumDodCheckType


class ModelLabReceiptCriterion(BaseModel):
    """A criterion statement read from a cited ticket's contract at the PR head."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    ticket: str = Field(description="Identifier of the cited ticket")
    statement: str = Field(
        description="The criterion statement as the contract states it"
    )
    check_type: EnumDodCheckType | None = Field(
        default=None,
        description=(
            "Type of the contract check that states this criterion; None for a "
            "ticket without a contract, whose statement is read by text pattern"
        ),
    )
