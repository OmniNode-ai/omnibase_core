# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Routing disposition for a concrete delegation terminal."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDelegationRoutingDisposition(StrEnum):
    """Whether terminal processing selected a concrete backend."""

    ROUTED = "routed"
    UNROUTED = "unrouted"


__all__: list[str] = ["EnumDelegationRoutingDisposition"]
