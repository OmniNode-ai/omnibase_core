# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import StrEnum


class EnumProcessRunnerState(StrEnum):
    """10-state FSM for process runner lifecycle.

    Canonical state machine for all overseer task execution.
    States progress from IDLE through terminal states COMPLETED and FAILED_TERMINAL.
    """

    IDLE = "idle"
    """Runner is initialized and waiting for a task assignment."""

    PLANNING = "planning"
    """Runner is analyzing the task and building an execution plan."""

    EXECUTING = "executing"
    """Runner is actively executing the planned steps."""

    VERIFYING = "verifying"
    """Runner is validating outputs against acceptance criteria."""

    RETRYING = "retrying"
    """Runner encountered a transient failure and is re-attempting."""

    WAITING_DEPENDENCY = "waiting_dependency"
    """Runner is blocked on an upstream dependency to become available."""

    ESCALATING = "escalating"
    """Runner has exceeded retry budget and is escalating to the overseer."""

    RECOVERING = "recovering"
    """Runner is executing a recovery procedure after a failure."""

    COMPLETED = "completed"
    """Terminal: runner finished successfully."""

    FAILED_TERMINAL = "failed_terminal"
    """Terminal: runner exhausted all recovery paths; task cannot proceed."""


__all__: list[str] = ["EnumProcessRunnerState"]
