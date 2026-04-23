# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Priority tiers for type-debt findings.

Output vocabulary for the LLM scorer in the ADK evaluation spike;
maps each mypy finding to one of four tiers of human-judged importance.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTypeDebtPriority(StrValueHelper, str, Enum):
    """Priority tiers for type-debt findings."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    NOISE = "noise"


__all__ = ["EnumTypeDebtPriority"]
