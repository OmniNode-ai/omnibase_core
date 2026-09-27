# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Execution-graph replay cursor mode vocabulary."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumExecutionGraphCursorMode(StrEnum):
    """Closed execution-graph replay cursor mode values."""

    LATEST = "latest"
    BOUNDED = "bounded"


__all__ = ["EnumExecutionGraphCursorMode"]
