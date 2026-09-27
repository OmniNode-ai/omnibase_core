# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Execution-graph replay verdict status vocabulary."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumExecutionGraphVerdictStatus(StrEnum):
    """Closed execution-graph replay verdict status values."""

    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNRESOLVED = "unresolved"


__all__ = ["EnumExecutionGraphVerdictStatus"]
