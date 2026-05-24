# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RoutingErrorClass: structured failure classes for LLM route rejection."""

from __future__ import annotations

from enum import Enum, unique


@unique
class RoutingErrorClass(str, Enum):
    """Failure classes emitted when the LLM router rejects a route."""

    PRIMARY_UNHEALTHY = "primary_unhealthy"
    FALLBACK_UNAUTHORIZED = "fallback_unauthorized"
    FALLBACK_UNAVAILABLE = "fallback_unavailable"
    REGISTRY_MISSING = "registry_missing"
    POLICY_INVALID = "policy_invalid"
    NO_ELIGIBLE_MODEL = "no_eligible_model"
    HEALTH_CHECK_FAILED = "health_check_failed"
    EXHAUSTED_RETRIES = "exhausted_retries"
    ENDPOINT_UNAVAILABLE = "endpoint_unavailable"


__all__ = ["RoutingErrorClass"]
