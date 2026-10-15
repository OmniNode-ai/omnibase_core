# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit of a context entry span (OMN-18531 / TC.1)."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumContextSpanUnit(StrEnum):
    """Whether span offsets count lines or characters."""

    LINE = "line"
    CHARACTER = "character"


__all__ = [
    "EnumContextSpanUnit",
]
