# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Stable reasons the routing order node refuses to answer."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDelegationRoutingOrderRefusal(StrEnum):
    """Stable reasons the routing order node refuses to answer."""

    OVERLAY_UNBOUND = "overlay_unbound"
    CHAIN_MISSING = "chain_missing"
    CHAIN_INVALID = "chain_invalid"
    OVERLAY_INVALID = "overlay_invalid"
    CONTRACT_UNREADABLE = "contract_unreadable"
    NOT_LAB_FIRST = "not_lab_first"


__all__ = ["EnumDelegationRoutingOrderRefusal"]
