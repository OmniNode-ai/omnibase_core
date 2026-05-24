# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumRouteRejectionReason — structured error codes for route resolution failure."""

from __future__ import annotations

from enum import Enum


class EnumRouteRejectionReason(str, Enum):
    """Routing error class for node_model_router rejection events."""

    UNKNOWN_KEY = "UNKNOWN_KEY"
    ENDPOINT_UNAVAILABLE = "ENDPOINT_UNAVAILABLE"
    POLICY_REJECTED = "POLICY_REJECTED"
    FALLBACK_EXHAUSTED = "FALLBACK_EXHAUSTED"


__all__: list[str] = ["EnumRouteRejectionReason"]
