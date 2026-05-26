# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Capability tier enum for routing policy decisions."""

from enum import StrEnum


class EnumCapabilityTier(StrEnum):
    """Model capability tier used to select the appropriate inference backend."""

    LOCAL = "local"
    CHEAP_FRONTIER = "cheap_frontier"
    MID_FRONTIER = "mid_frontier"
    EXPENSIVE_FRONTIER = "expensive_frontier"


__all__: list[str] = ["EnumCapabilityTier"]
