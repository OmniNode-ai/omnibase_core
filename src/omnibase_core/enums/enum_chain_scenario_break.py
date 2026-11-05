# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Named break a generated chain test must turn red under (OMN-22478)."""

from __future__ import annotations

from enum import Enum


class EnumChainScenarioBreak(str, Enum):
    """Named break a generated chain test must turn red under (OMN-22478)."""

    DROP_TERMINAL_PUBLISH = "DROP_TERMINAL_PUBLISH"
    WRONG_CORRELATION_ID = "WRONG_CORRELATION_ID"
    SKIPPED_REDUCER_UPDATE = "SKIPPED_REDUCER_UPDATE"


__all__ = ["EnumChainScenarioBreak"]
