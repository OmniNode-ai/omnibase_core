# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Execution-graph replay node kind vocabulary."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumExecutionGraphNodeKind(StrEnum):
    """Closed execution-graph replay node kind values."""

    HOP = "hop"
    REROUTE_EVIDENCE = "reroute_evidence"


__all__ = ["EnumExecutionGraphNodeKind"]
