# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Data provenance enum for tracking origin quality of displayed values."""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumDataProvenance"]


@unique
class EnumDataProvenance(StrValueHelper, str, Enum):
    """Origin quality classification for data values displayed in dashboards or reports."""

    DEMO_SEEDED = "demo_seeded"
    DEMO_PROJECTED_SHORTCUT = "demo_projected_shortcut"
    MEASURED = "measured"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value: object) -> EnumDataProvenance | None:
        """Return no implicit aliases for unknown data-provenance values."""
        return None
