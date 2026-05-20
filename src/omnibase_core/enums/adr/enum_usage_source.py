# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Usage source enum for LLM call evidence (OMN-10691)."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumUsageSource(UtilStrValueHelper, str, Enum):
    """Indicates whether token usage was measured, estimated, or unknown."""

    MEASURED = "MEASURED"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"
