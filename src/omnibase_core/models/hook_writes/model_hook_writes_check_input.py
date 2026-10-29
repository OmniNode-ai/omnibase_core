# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the pure hook-writes check (OMN-21498)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.hook_writes.model_hook_writes_overlay import (
    ModelHookWritesOverlay,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)

__all__ = ["ModelHookWritesCheckInput"]


class ModelHookWritesCheckInput(BaseModel):
    """Overlay rule values and repository-relative hook files to judge in order."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    overlay: ModelHookWritesOverlay
    files: tuple[ModelSourceFile, ...] = Field(default=())
