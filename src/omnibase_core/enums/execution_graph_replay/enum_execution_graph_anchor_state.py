# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Execution-graph replay anchor state vocabulary."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumExecutionGraphAnchorState(StrEnum):
    """Closed execution-graph replay anchor state values."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


__all__ = ["EnumExecutionGraphAnchorState"]
