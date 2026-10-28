# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One overlay-defined command signal for the hook-writes check (OMN-21433)."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ModelHookWritesSignal"]


class ModelHookWritesSignal(BaseModel):
    """A rewriting command pattern and an optional check-only exception pattern."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    id: str
    pattern: str
    unless: str | None = None
    reason: str = Field(min_length=10)

    @field_validator("pattern", "unless")
    @classmethod
    def _compiles(cls, value: str | None) -> str | None:
        """Reject invalid regular expressions before any hook is judged."""
        if value is not None:
            try:
                re.compile(value)
            except re.error as exc:
                raise ValueError(f"invalid regular expression: {exc}") from exc
        return value
