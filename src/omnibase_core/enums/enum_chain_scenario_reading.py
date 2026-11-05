# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Reading a node subject shows after a chain scenario (OMN-22478)."""

from __future__ import annotations

from enum import Enum


class EnumChainScenarioReading(str, Enum):
    """Reading a node subject shows after a chain scenario (OMN-22478)."""

    WORKING = "WORKING"
    NOT_WORKING = "NOT_WORKING"
    UNKNOWN = "UNKNOWN"


__all__ = ["EnumChainScenarioReading"]
