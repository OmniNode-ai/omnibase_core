# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Doctrine coverage enum for classifying enforcement level of doctrine rules."""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper

__all__ = ["EnumDoctrineCoverage"]


@unique
class EnumDoctrineCoverage(UtilStrValueHelper, str, Enum):
    """Enforcement classification for doctrine coverage of a node or widget."""

    UNCOVERED = "uncovered"
    ADVISORY = "advisory"
    ENFORCED = "enforced"

    @classmethod
    def _missing_(cls, value: object) -> EnumDoctrineCoverage | None:
        """Return no implicit aliases for unknown doctrine-coverage values."""
        return None
