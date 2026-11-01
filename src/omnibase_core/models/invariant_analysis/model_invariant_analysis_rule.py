# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed rule row with validated parameters (OMN-21565)."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumSeverity

__all__ = ["ModelInvariantAnalysisRule"]


class ModelInvariantAnalysisRule(BaseModel):
    """Typed rule row with validated parameters."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    enabled: bool = Field(description="Whether this row emits findings")
    severity: EnumSeverity = Field(description="Finding severity")
    texts: dict[str, str] = Field(description="Text and expression parameters")
    lists: dict[str, tuple[str, ...]] = Field(description="Sequence parameters")
    integers: dict[str, int] = Field(description="Integer parameters")

    def pattern(self, name: str) -> re.Pattern[str]:
        """Compile an already validated expression."""
        return re.compile(self.texts[name])
