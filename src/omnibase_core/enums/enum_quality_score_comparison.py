# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed comparison between a delegation quality score and its required bar."""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumQualityScoreComparison(str, Enum):
    """Machine-readable relationship between a quality score and its bar."""

    BELOW_BAR = "below_bar"
    AT_OR_ABOVE_BAR = "at_or_above_bar"


__all__: list[str] = ["EnumQualityScoreComparison"]
