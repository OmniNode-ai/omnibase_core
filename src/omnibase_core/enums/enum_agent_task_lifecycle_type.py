# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumAgentTaskLifecycleType: remote-agent task lifecycle event types (OMN-9623).

Distinct from EnumDelegationState which models the orchestrator FSM transitions
(RECEIVED, ROUTED, etc.). This enum classifies the lifecycle events emitted by
a remote agent peer, translated from the A2A protocol by HandlerA2ATask.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumAgentTaskLifecycleType(StrValueHelper, str, Enum):
    """Lifecycle event types emitted by a remote agent task.

    Classifies the observable state transitions of a remote agent task
    as received from the peer (e.g. via the A2A protocol) and translated
    into typed Kafka events by the bridge effect node.

    Values:
        SUBMITTED: Task has been submitted to the remote agent.
        ACCEPTED: Remote agent has accepted the task.
        PROGRESS: Remote agent is actively working on the task.
        ARTIFACT: Remote agent has produced an intermediate artifact.
        COMPLETED: Remote agent has completed the task successfully.
        FAILED: Remote agent reported an unrecoverable failure.
        TIMED_OUT: Task exceeded its allowed execution window.
        CANCELED: Task was canceled before completion.
    """

    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    PROGRESS = "PROGRESS"
    ARTIFACT = "ARTIFACT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELED = "CANCELED"


__all__ = ["EnumAgentTaskLifecycleType"]
