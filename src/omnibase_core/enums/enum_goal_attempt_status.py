# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Durable states for a pre-allocated goal verification attempt."""

from __future__ import annotations

from enum import StrEnum


class EnumGoalAttemptStatus(StrEnum):
    """Observed state of one immutable allocated attempt."""

    ALLOCATED = "allocated"
    RUNNING = "running"
    PASS = "pass"
    FAIL = "fail"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    MISSING = "missing"


__all__ = ["EnumGoalAttemptStatus"]
