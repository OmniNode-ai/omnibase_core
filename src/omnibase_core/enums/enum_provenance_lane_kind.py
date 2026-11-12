# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Provenance Lane Kind Enum.

What kind of emitter an OTHER lane is.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumProvenanceLaneKind(UtilStrValueHelper, str, Enum):
    """Kind of emitter for an OTHER provenance lane."""

    MAC_UNIT = "mac_unit"
    LANE_WORKTREE = "lane_worktree"
    HAND_RUN = "hand_run"


__all__: list[str] = ["EnumProvenanceLaneKind"]
