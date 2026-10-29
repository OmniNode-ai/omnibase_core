# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One finding of a baselined hook, with the normalized source text it matches on."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelSourceFinding"]


class ModelSourceFinding(BaseModel):
    """A finding located in one file.

    The baseline identity is ``(path, rule, text)``; the line is for display only,
    so an edit above a finding never breaks its baseline entry. A finding that is
    not ``baselinable`` (an unreadable or unparseable file) always fails.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(min_length=1)
    line: int = Field(ge=0)
    rule: str = Field(min_length=1)
    text: str
    message: str = Field(min_length=1)
    baselinable: bool = True

    def key(self) -> tuple[str, str, str]:
        """The identity a baseline entry matches this finding on."""
        return (self.path, self.rule, self.text)
