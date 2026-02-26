# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Routing models for tiered authenticated dependency resolution.

This module provides the type system for trust-domain-scoped, tiered
dependency resolution. All models are immutable (frozen) value objects
suitable for serialization, caching, and concurrent read access.

Resolution Flow
----------------
1. A capability dependency enters the tiered resolver.
2. The resolver iterates through trust domains ordered by tier.
3. Each tier attempt is recorded as a ``ModelTierAttempt``.
4. On success, a ``ModelRoutePlan`` with ``ModelResolutionRouteHop`` entries is built.
5. The full result is wrapped in ``ModelTieredResolutionResult``.

.. versionadded:: 0.21.0
    Phase 1 of authenticated dependency resolution (OMN-2890).
"""

from omnibase_core.models.routing.model_hop_constraints import ModelHopConstraints
from omnibase_core.models.routing.model_resolution_route_hop import (
    ModelResolutionRouteHop,
)
from omnibase_core.models.routing.model_route_plan import ModelRoutePlan
from omnibase_core.models.routing.model_tier_attempt import ModelTierAttempt
from omnibase_core.models.routing.model_tiered_resolution_result import (
    ModelTieredResolutionResult,
)
from omnibase_core.models.routing.model_trust_domain import ModelTrustDomain

__all__ = [
    "ModelHopConstraints",
    "ModelResolutionRouteHop",
    "ModelRoutePlan",
    "ModelTierAttempt",
    "ModelTieredResolutionResult",
    "ModelTrustDomain",
]
