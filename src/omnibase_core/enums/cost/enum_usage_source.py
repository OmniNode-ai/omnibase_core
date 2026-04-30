# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Usage source enum for model-call cost attribution."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumUsageSource(StrValueHelper, str, Enum):
    """Source quality for token/cost usage attribution."""

    MEASURED = "measured"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"
