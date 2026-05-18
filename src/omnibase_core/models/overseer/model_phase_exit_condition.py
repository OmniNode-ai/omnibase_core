# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelPhaseExitCondition — typed exit condition for a session phase (OMN-11226)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ModelPhaseExitCondition(BaseModel):
    """A single typed exit condition for a ModelSessionPhaseSpec."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    condition_type: Literal[
        "pr_state", "worker_count", "custom_probe", "task_complete", "time_elapsed"
    ]

    # pr_state
    repo: str | None = None
    pr_number: int | None = None
    required_state: Literal["merged", "closed", "open"] | None = None

    # worker_count / time_elapsed
    operator: Literal["eq", "lt", "gt", "le", "ge"] | None = None
    value: int | None = None

    # custom_probe
    command: str | None = None
    expected_exit_code: int | None = None

    # task_complete
    task_name: str | None = None


__all__ = ["ModelPhaseExitCondition"]
