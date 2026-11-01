# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One validated registry entry (OMN-21565)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelInvariantEntry"]


class ModelInvariantEntry(BaseModel):
    """One validated registry entry."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    id: str = Field(description="Registry identifier")
    statement: str = Field(description="Settled invariant statement")
    scope: tuple[str, ...] = Field(description="Registry scope tags")
    status: str = Field(description="Registry lifecycle status")
    superseded_by: str | None = Field(
        default=None, description="Replacement identifier"
    )
