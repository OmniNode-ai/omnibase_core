# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Execution-graph replay edge kind vocabulary."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumExecutionGraphEdgeKind(StrEnum):
    """Closed execution-graph replay edge kind values."""

    CAUSED = "caused"
    REROUTED = "rerouted"
    VERIFIED = "verified"
    ANCHORED = "anchored"


__all__ = ["EnumExecutionGraphEdgeKind"]
