# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Filesystem facts captured by the runtime."""

from pydantic import BaseModel, ConfigDict


class ModelMarkdownLinkInventoryEntry(BaseModel):
    """Path existence, symlink resolution and target heading inventory."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str
    resolved_path: str
    exists: bool = True
    anchors: tuple[str, ...] = ()
    resolution_error: str | None = None
