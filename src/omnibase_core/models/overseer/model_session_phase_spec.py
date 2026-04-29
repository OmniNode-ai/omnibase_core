# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelSessionPhaseSpec — specification for a single session phase (OMN-10251)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.overseer.model_dispatch_item import ModelDispatchItem


class ModelSessionPhaseSpec(BaseModel):
    """Specification for a single session phase."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    phase_name: str
    required: bool = True
    timeout_seconds: int = 3600
    halt_on_failure: bool = False
    success_criteria: list[str] = Field(default_factory=list)
    dispatch_items: tuple[ModelDispatchItem, ...] = ()


__all__ = ["ModelSessionPhaseSpec"]
