# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Kind of a contract-declared chain scenario case (OMN-22478)."""

from __future__ import annotations

from enum import Enum


class EnumChainScenarioKind(str, Enum):
    """Kind of a contract-declared chain scenario case (OMN-22478)."""

    GOLDEN = "GOLDEN"
    ERROR = "ERROR"


__all__ = ["EnumChainScenarioKind"]
