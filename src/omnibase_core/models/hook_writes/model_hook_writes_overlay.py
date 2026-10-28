# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Overlay-owned rule values for the hook-writes check (OMN-21433)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.hook_writes.model_hook_writes_rewriting_hook import (
    ModelHookWritesRewritingHook,
)
from omnibase_core.models.hook_writes.model_hook_writes_signal import (
    ModelHookWritesSignal,
)

__all__ = ["ModelHookWritesOverlay"]


class ModelHookWritesOverlay(BaseModel):
    """Command signals and known rewriting hook ids loaded from an overlay."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    signals: tuple[ModelHookWritesSignal, ...] = Field(default=())
    rewriting_hooks: tuple[ModelHookWritesRewritingHook, ...] = Field(default=())

    def rewriting_hook(self, hook_id: str) -> ModelHookWritesRewritingHook | None:
        """Return the rewriting rule for this hook id, when the overlay has one."""
        return next((hook for hook in self.rewriting_hooks if hook.id == hook_id), None)
