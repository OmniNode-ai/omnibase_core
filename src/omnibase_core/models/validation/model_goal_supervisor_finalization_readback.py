# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed post-persist evidence readback shared by supervisor providers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_goal_attempt_allocation_snapshot import (
    ModelGoalAttemptAllocationSnapshot,
)
from omnibase_core.models.validation.model_goal_execution_result import (
    ModelGoalExecutionResult,
)
from omnibase_core.models.validation.model_goal_supervisor_execution_receipt import (
    ModelGoalSupervisorExecutionReceipt,
)


class ModelGoalSupervisorFinalizationReadback(BaseModel):
    """Post-persist attempt, canonical result, and detached execution receipt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    attempt_snapshot: ModelGoalAttemptAllocationSnapshot
    result: ModelGoalExecutionResult
    receipt: ModelGoalSupervisorExecutionReceipt


__all__ = ["ModelGoalSupervisorFinalizationReadback"]
