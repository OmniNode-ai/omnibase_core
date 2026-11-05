# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Why a node refuses a chain scenario it cannot yet carry (OMN-22478)."""

from __future__ import annotations

from enum import Enum


class EnumChainScenarioRefusalKind(str, Enum):
    """Why a node refuses a chain scenario it cannot yet carry (OMN-22478)."""

    FAILURE_NOT_TYPED = "FAILURE_NOT_TYPED"
    NO_OBSERVABLE_OUTPUT = "NO_OBSERVABLE_OUTPUT"
    NEEDS_LIVE_DEPENDENCY = "NEEDS_LIVE_DEPENDENCY"
    DEPENDENCY_NOT_INJECTABLE = "DEPENDENCY_NOT_INJECTABLE"


__all__ = ["EnumChainScenarioRefusalKind"]
