# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""EnumQualityGateResult: quality gate verdict enum for delegation escalation (OMN-10617)."""

from __future__ import annotations

from enum import Enum


class EnumQualityGateResult(str, Enum):
    """Quality gate verdict that triggered a model escalation."""

    PASS = "pass"
    FAIL_DETERMINISTIC = "fail_deterministic"
    FAIL_HEURISTIC = "fail_heuristic"


__all__ = ["EnumQualityGateResult"]
