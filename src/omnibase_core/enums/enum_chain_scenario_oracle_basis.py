# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Where a chain scenario expectation comes from (OMN-22478). RECORDED_FROM_OUTPUT is not independent and is refused."""

from __future__ import annotations

from enum import Enum


class EnumChainScenarioOracleBasis(str, Enum):
    """Where a chain scenario expectation comes from (OMN-22478). RECORDED_FROM_OUTPUT is not independent and is refused."""

    STATED_BY_PERSON = "STATED_BY_PERSON"
    CONTRACT_RULE = "CONTRACT_RULE"
    RECORDED_FROM_OUTPUT = "RECORDED_FROM_OUTPUT"


__all__ = ["EnumChainScenarioOracleBasis"]
