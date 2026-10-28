# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""An overlay-defined rewriting hook id and its check-only arguments (OMN-21433)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelHookWritesRewritingHook"]


class ModelHookWritesRewritingHook(BaseModel):
    """A known rewriting hook and the tokens that make it check-only."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    id: str
    check_only_args: tuple[str, ...] = Field(default=())
    reason: str = Field(min_length=10)
