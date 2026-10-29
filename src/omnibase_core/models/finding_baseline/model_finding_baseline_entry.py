# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One tolerated finding in a hook's baseline file."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelFindingBaselineEntry"]


class ModelFindingBaselineEntry(BaseModel):
    """File path, rule id and normalized offending source text; never a line number.

    Entries are counted as a multiset: two identical findings in one file need two
    identical entries.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(min_length=1)
    rule: str = Field(min_length=1)
    text: str

    def key(self) -> tuple[str, str, str]:
        """The identity a finding is matched on."""
        return (self.path, self.rule, self.text)
