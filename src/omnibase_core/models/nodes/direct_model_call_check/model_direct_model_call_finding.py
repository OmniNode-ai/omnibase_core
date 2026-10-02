# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelDirectModelCallFinding: one direct model call site, keyed by what it is, never by line number (OMN-20295)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_direct_model_call_kind import EnumDirectModelCallKind

__all__ = ["ModelDirectModelCallFinding"]


class ModelDirectModelCallFinding(BaseModel):
    """One direct model call site, keyed by what it is, never by line number."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Repository-relative path")
    line: int = Field(ge=1, description="1-based line of the site")
    kind: EnumDirectModelCallKind = Field(description="Site kind")
    symbol: str = Field(
        description="Enclosing function qualname, '<module>' or a shell function"
    )
    target: str = Field(
        description="What is called: an SDK, a CLI, 'http', or the callee path::symbol"
    )
    evidence: str = Field(description="Why the site is a model call, for the reader")

    def key(self) -> tuple[str, str, str, str]:
        return (self.path, self.kind, self.symbol, self.target)
