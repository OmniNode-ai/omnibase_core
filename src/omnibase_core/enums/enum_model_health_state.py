# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Enum for model health states used by the delegation routing system (OMN-10611)."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumModelHealthState(StrValueHelper, str, Enum):
    """Observable health state of a model endpoint for delegation routing.

    States:
        AVAILABLE: Model responds within its declared latency SLA.
        DEGRADED: Model responds but latency exceeds latency_threshold_ms.
        UNAVAILABLE: Model does not respond or returns errors.
    """

    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


__all__ = ["EnumModelHealthState"]
