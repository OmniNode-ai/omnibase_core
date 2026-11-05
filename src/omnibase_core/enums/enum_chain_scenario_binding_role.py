# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Role of a dependency a chain scenario binds into a handler (OMN-22478)."""

from __future__ import annotations

from enum import Enum


class EnumChainScenarioBindingRole(str, Enum):
    """Role of a dependency a chain scenario binds into a handler (OMN-22478)."""

    DEPENDENCY = "DEPENDENCY"
    REDUCER_STATE = "REDUCER_STATE"


__all__ = ["EnumChainScenarioBindingRole"]
