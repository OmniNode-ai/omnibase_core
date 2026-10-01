# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Outcomes observed for one protected verification attempt."""

from __future__ import annotations

from enum import StrEnum


class EnumGoalSupervisorOutcome(StrEnum):
    """Observed result of one protected verification attempt."""

    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    INCOMPLETE = "incomplete"


__all__ = ["EnumGoalSupervisorOutcome"]
