# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Closed reasons a delegation terminal did not select a backend."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDelegationUnroutedReason(StrEnum):
    """Why routing did not select a backend."""

    NO_ELIGIBLE_BACKEND = "no_eligible_backend"
    ROUTING_POLICY_REJECTED = "routing_policy_rejected"
    ROUTING_CONFIGURATION_INVALID = "routing_configuration_invalid"


__all__: list[str] = ["EnumDelegationUnroutedReason"]
