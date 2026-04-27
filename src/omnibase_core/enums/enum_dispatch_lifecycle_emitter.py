# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dispatch Lifecycle Emitter enum for ModelDispatchLifecycleEvent (OMN-9885)."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDispatchLifecycleEmitter(StrValueHelper, str, Enum):
    """Identifies which actor emitted a lifecycle event.

    Per the Task 10 emitter responsibility table:
    - DISPATCHER: emits ACCEPTED only
    - CONSUMER: emits STARTED, HEARTBEAT, TERMINAL_SUCCESS, TERMINAL_FAILURE
    - ORCHESTRATOR: emits TIMEOUT, CANCELLED
    - DLQ_WRITER: emits DLQ
    """

    DISPATCHER = "dispatcher"
    CONSUMER = "consumer"
    ORCHESTRATOR = "orchestrator"
    DLQ_WRITER = "dlq_writer"


__all__ = ["EnumDispatchLifecycleEmitter"]
