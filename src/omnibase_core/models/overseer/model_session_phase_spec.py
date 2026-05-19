# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelSessionPhaseSpec — specification for a single session phase (OMN-10251, OMN-11225)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.overseer.enum_completion_outcome import EnumCompletionOutcome
from omnibase_core.models.overseer.model_dispatch_item import ModelDispatchItem
from omnibase_core.models.overseer.model_phase_exit_condition import (
    ModelPhaseExitCondition,
)
from omnibase_core.models.overseer.model_session_halt_condition import (
    ModelSessionHaltCondition,
)


class ModelSessionPhaseSpec(BaseModel):
    """Specification for a single session phase."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    phase_name: str
    required: bool = True
    timeout_seconds: int = Field(default=3600, gt=0)
    halt_on_failure: bool = False
    success_criteria: list[str] = Field(default_factory=list)
    dispatch_items: tuple[ModelDispatchItem, ...] = ()
    required_outcomes: tuple[EnumCompletionOutcome, ...] = ()
    halt_conditions: tuple[ModelSessionHaltCondition, ...] = ()
    exit_conditions: tuple[ModelPhaseExitCondition, ...] = ()
    max_duration_minutes: int | None = Field(default=None, gt=0)
    budget_warning_pct: int = Field(default=80, gt=0, le=100)
    parallel_with: tuple[str, ...] = ()


__all__ = ["ModelSessionPhaseSpec"]
