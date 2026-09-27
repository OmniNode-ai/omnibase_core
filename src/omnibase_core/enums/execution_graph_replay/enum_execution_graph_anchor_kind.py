# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Execution-graph replay anchor kind vocabulary."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumExecutionGraphAnchorKind(StrEnum):
    """Closed execution-graph replay anchor kind values."""

    SESSION = "session"
    NONE = "none"


__all__ = ["EnumExecutionGraphAnchorKind"]
