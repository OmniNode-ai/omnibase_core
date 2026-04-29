# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelOvernightPhaseSpec — specification for a single overnight phase (OMN-10251)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.overseer.enum_completion_outcome import EnumCompletionOutcome
from omnibase_core.models.overseer.model_dispatch_item import ModelDispatchItem
from omnibase_core.models.overseer.model_overnight_halt_condition import (
    ModelOvernightHaltCondition,
)


class ModelOvernightPhaseSpec(BaseModel):
    """Specification for a single overnight phase."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    phase_name: str
    required: bool = True
    timeout_seconds: int = Field(default=3600, gt=0)
    halt_on_failure: bool = False
    success_criteria: list[str] = Field(default_factory=list)
    dispatch_items: tuple[ModelDispatchItem, ...] = ()
    required_outcomes: tuple[EnumCompletionOutcome, ...] = ()
    halt_conditions: tuple[ModelOvernightHaltCondition, ...] = ()


__all__ = ["ModelOvernightPhaseSpec"]
