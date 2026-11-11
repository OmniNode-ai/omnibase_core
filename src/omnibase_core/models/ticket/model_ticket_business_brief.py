# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The business brief of a ticket: the five plain-language headings (OMN-23412)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

_MAX_STRING_LENGTH = 10000


class ModelTicketBusinessBrief(BaseModel):
    """The "In plain terms" section a non-technical reader can follow.

    Five headings, no status line (the ticket tracker shows status), as the
    operator amended OMN-23412 on 2026-11-10 about 06:25Z. Each is required
    and non-empty so a brief missing a heading is refused naming it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    what_this_is: str = Field(description="What this is", max_length=_MAX_STRING_LENGTH)
    why_it_matters: str = Field(
        description="Why it matters", max_length=_MAX_STRING_LENGTH
    )
    done_looks_like: str = Field(
        description="Done looks like", max_length=_MAX_STRING_LENGTH
    )
    risk: str = Field(description="Risk", max_length=_MAX_STRING_LENGTH)
    depends_on: str = Field(description="Depends on", max_length=_MAX_STRING_LENGTH)

    @field_validator(
        "what_this_is",
        "why_it_matters",
        "done_looks_like",
        "risk",
        "depends_on",
    )
    @classmethod
    def must_be_nonempty(cls, v: str) -> str:
        """Reject empty strings and whitespace-only values."""
        if not v.strip():
            raise ValueError("must be non-empty and not whitespace-only")
        return v


__all__ = ["ModelTicketBusinessBrief"]
