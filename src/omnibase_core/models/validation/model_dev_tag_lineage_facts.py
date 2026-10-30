# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resolved facts; None always means unresolved, never success."""

from pydantic import BaseModel, ConfigDict


class ModelDevTagLineageFacts(BaseModel):
    """Partial evidence is retained when a later git step fails."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    tag_exists: bool | None = None
    commit: str | None = None
    version: str | None = None
    on_branch: bool | None = None
    detail: str
