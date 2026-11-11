# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Kinds of rung in a delegation routing order answer."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDelegationRoutingOrderRungKind(StrEnum):
    """Whether a routing order rung is a ladder tier or a harness slot."""

    LADDER = "ladder"
    HARNESS = "harness"


__all__ = ["EnumDelegationRoutingOrderRungKind"]
