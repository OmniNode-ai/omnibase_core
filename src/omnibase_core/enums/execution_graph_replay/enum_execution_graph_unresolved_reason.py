# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Execution-graph replay unresolved reason vocabulary."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumExecutionGraphUnresolvedReason(StrEnum):
    """Closed execution-graph replay unresolved reason values."""

    MISSING_PARENT = "missing_parent"
    PARENT_OUTSIDE_CURSOR = "parent_outside_cursor"
    MISSING_ANCHOR = "missing_anchor"
    MISSING_VERDICT = "missing_verdict"


__all__ = ["EnumExecutionGraphUnresolvedReason"]
