# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The sixteen states of a lane work workflow (OMN-26699, plan section 3.2)."""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumLaneWorkState(UtilStrValueHelper, str, Enum):
    """State of one lane work workflow; `handed_off` and `blocked` are terminal."""

    QUEUED = "queued"
    AWAITING_WORKER = "awaiting_worker"
    CONFIRMING_CLAIM = "confirming_claim"
    CLAIMED = "claimed"
    RED = "red"
    DIAGNOSING = "diagnosing"
    FIXING = "fixing"
    WAITING_RELEASE = "waiting_release"
    PUSHING = "pushing"
    PROVING = "proving"
    PROVEN = "proven"
    HANDING_OFF = "handing_off"
    CONFIRMING_HANDOFF = "confirming_handoff"
    HELP_REQUESTED = "help_requested"
    HANDED_OFF = "handed_off"
    BLOCKED = "blocked"
