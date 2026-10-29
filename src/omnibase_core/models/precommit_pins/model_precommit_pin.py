# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One pre-commit repository entry with its source location (OMN-21495)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelPrecommitPin"]


class ModelPrecommitPin(BaseModel):
    """A repository URL as written, its rev scalar and the entry's hook IDs."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(min_length=1)
    rev: str = Field(min_length=1)
    line: int = Field(ge=1)
    hook_ids: tuple[str, ...]
