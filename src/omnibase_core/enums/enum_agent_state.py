# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Closed enum for agent lifecycle states (OMN-1847).

CLOSED ENUM: Adding new states is a BREAKING CHANGE requiring:
- Version increment of status_schema_version in ModelAgentStatusEvent
- Consumer updates across all downstream subscribers
- Migration plan for existing state machine transitions
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumAgentState(StrValueHelper, str, Enum):
    """Closed enum for agent states. Version: 1.

    Represents the observable lifecycle state of an agent as reported
    through the Agent Status MCP Protocol. All transitions are
    observational only — they must never directly cause state mutation
    without passing through a reducer.

    States:
        IDLE: Agent is available and waiting for work.
        WORKING: Agent is actively executing a task.
        BLOCKED: Agent cannot proceed due to an external dependency.
        AWAITING_INPUT: Agent requires human or system input to continue.
        FINISHED: Agent has successfully completed its assigned work.
        ERROR: Agent encountered an unrecoverable error.
    """

    IDLE = "idle"
    WORKING = "working"
    BLOCKED = "blocked"
    AWAITING_INPUT = "awaiting_input"
    FINISHED = "finished"
    ERROR = "error"


__all__ = ["EnumAgentState"]
