# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Execution-graph replay endpoint kind vocabulary."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumExecutionGraphEndpointKind(StrEnum):
    """Closed execution-graph replay endpoint kind values."""

    NODE = "node"
    VERDICT = "verdict"
    SESSION_ANCHOR = "session_anchor"


__all__ = ["EnumExecutionGraphEndpointKind"]
