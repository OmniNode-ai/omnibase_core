# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelDirectModelCallBaselineEntry: a pre-existing site the ratchet tolerates until its cutover ticket lands (OMN-20295)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_direct_model_call_kind import EnumDirectModelCallKind

__all__ = ["ModelDirectModelCallBaselineEntry"]


class ModelDirectModelCallBaselineEntry(BaseModel):
    """A pre-existing site the ratchet tolerates until its cutover ticket lands.

    Repeated identical keys in one file appear as repeated entries (a multiset).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Repository-relative path")
    kind: EnumDirectModelCallKind = Field(description="Site kind")
    symbol: str = Field(description="Enclosing symbol")
    target: str = Field(description="What is called")
    ticket: str = Field(
        pattern=r"^OMN-[0-9]+$", description="The ticket that removes this site"
    )
    expires: date = Field(
        description="After this date the entry no longer covers its site"
    )

    def key(self) -> tuple[str, str, str, str]:
        return (self.path, self.kind, self.symbol, self.target)
