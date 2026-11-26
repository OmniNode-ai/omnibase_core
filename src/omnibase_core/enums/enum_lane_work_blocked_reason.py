# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Why a lane work workflow ended blocked (OMN-26699, plan sections 3.4 and 3.7)."""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumLaneWorkBlockedReason(UtilStrValueHelper, str, Enum):
    """The closed list of reasons a `blocked` terminal may carry."""

    WORKER_NEVER_STARTED = "worker_never_started"
    NOT_CLAIMED = "not_claimed"
    WORKER_LOST = "worker_lost"
    HELP_EXHAUSTED = "help_exhausted"
