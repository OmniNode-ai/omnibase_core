# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Source of candidate answers."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumModelSwapAnswerSource(UtilStrValueHelper, str, Enum):
    """Source of candidate answers."""

    LIVE = "live"
    RECORDED = "recorded"


__all__ = ["EnumModelSwapAnswerSource"]
