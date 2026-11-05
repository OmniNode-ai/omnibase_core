# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""How a chain scenario binds a dependency into a handler (OMN-22478)."""

from __future__ import annotations

from enum import Enum


class EnumChainScenarioBindingTarget(str, Enum):
    """How a chain scenario binds a dependency into a handler (OMN-22478)."""

    CONSTRUCTOR_KWARG = "CONSTRUCTOR_KWARG"
    ATTRIBUTE = "ATTRIBUTE"


__all__ = ["EnumChainScenarioBindingTarget"]
