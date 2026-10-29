# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Terminal validation failures."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumModelSwapValidationFailure(UtilStrValueHelper, str, Enum):
    """Terminal validation failures."""

    NO_NEUTRAL_JUDGE = "no_neutral_judge"
    NEEDS_INPUT = "needs_input"
    SPEND_CAP = "spend_cap"
    TOOL_FAILED = "tool_failed"
    SCHEMA_MISMATCH = "schema_mismatch"
    REPLAY_SET_MISSING = "replay_set_missing"
    REPOSITORY_REFUSED = "repository_refused"
    UNPINNED_TOOL = "unpinned_tool"
    EGRESS_VIOLATION = "egress_violation"
    TIMEOUT = "timeout"


__all__ = ["EnumModelSwapValidationFailure"]
