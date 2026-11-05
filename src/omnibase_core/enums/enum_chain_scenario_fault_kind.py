# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Defined fault an error chain scenario injects (OMN-22478)."""

from __future__ import annotations

from enum import Enum


class EnumChainScenarioFaultKind(str, Enum):
    """Defined fault an error chain scenario injects (OMN-22478)."""

    BAD_PAYLOAD = "BAD_PAYLOAD"
    HANDLER_ERROR = "HANDLER_ERROR"
    DEPENDENCY_DOWN = "DEPENDENCY_DOWN"
    MISSED_DEADLINE = "MISSED_DEADLINE"


__all__ = ["EnumChainScenarioFaultKind"]
