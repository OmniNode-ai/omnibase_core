# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A single ordered comparison of candidate and reference answers."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumModelSwapJudgeVerdict(UtilStrValueHelper, str, Enum):
    """A single ordered comparison of candidate and reference answers."""

    EQUIVALENT = "equivalent"
    MINOR_DRIFT = "minor_drift"
    DIVERGENT = "divergent"


__all__ = ["EnumModelSwapJudgeVerdict"]
