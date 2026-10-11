# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Kafka topic constants for Debug Intelligence events.

Using ``StrEnum`` makes topic names part of the typed external contract
surface — consistent with omnibase_core's topic enum conventions.

Ticket: OMN-3556
"""

from __future__ import annotations

from enum import StrEnum


class DebugIntelTopic(StrEnum):
    """Kafka topics consumed and produced by the debug_intel module.

    Input topics (kind=cmd) are consumed by effect nodes.
    Output topics (kind=evt) are emitted by effect nodes.

    Convention: onex.{kind}.{producer}.{event-name}.v{n}
      kind=cmd  for commands/inputs (consumed)
      kind=evt  for events/outputs  (produced)
    """

    # Input: CI failure detected by CI webhook handler (external producer)
    CI_FAILURE_DETECTED = "onex.cmd.omniintelligence.ci-failure-detected.v1"

    # Input: CI run passed after prior failure — used to create FixRecord
    CI_RECOVERY_DETECTED = "onex.cmd.omniintelligence.ci-recovery-detected.v1"

    # Output: TriggerRecord created (streak threshold crossed)
    DEBUG_TRIGGER_RECORD_CREATED = (
        "onex.evt.omniintelligence.debug-trigger-record-created.v1"
    )

    # Output: FixRecord created (CI recovered, TriggerRecord resolved)
    DEBUG_FIX_RECORD_CREATED = "onex.evt.omniintelligence.debug-fix-record-created.v1"


__all__ = [
    "DebugIntelTopic",
]
