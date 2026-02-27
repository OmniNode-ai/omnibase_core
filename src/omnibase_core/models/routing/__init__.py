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
4. For tiers beyond ``local_exact``, capability tokens are verified
   via ``ServiceCapabilityTokenVerifier`` producing ``ModelResolutionProof``.
5. Classification gates (Phase 4) check whether the data classification
   permits resolution at the current tier.
6. On success, a ``ModelRoutePlan`` with ``ModelResolutionRouteHop`` entries is built.
7. The full result is wrapped in ``ModelTieredResolutionResult``.

.. versionadded:: 0.21.0
    Phase 1 of authenticated dependency resolution (OMN-2890).
    Phase 3 adds ModelCapabilityToken and ModelResolutionProof (OMN-2892).
    Phase 4 adds ModelClassificationGate, ModelRedactionPolicy,
    and ModelPolicyBundle (OMN-2893).
    Phase 6 adds ModelResolutionEvent for the resolution event
    ledger (OMN-2895).
"""

from omnibase_core.models.routing.model_capability_token import ModelCapabilityToken
from omnibase_core.models.routing.model_classification_gate import (
    ModelClassificationGate,
)
from omnibase_core.models.routing.model_hop_constraints import ModelHopConstraints
from omnibase_core.models.routing.model_policy_bundle import ModelPolicyBundle
from omnibase_core.models.routing.model_redaction_policy import ModelRedactionPolicy
from omnibase_core.models.routing.model_resolution_event import ModelResolutionEvent
from omnibase_core.models.routing.model_resolution_proof import ModelResolutionProof
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
    "ModelCapabilityToken",
    "ModelClassificationGate",
    "ModelHopConstraints",
    "ModelPolicyBundle",
    "ModelRedactionPolicy",
    "ModelResolutionEvent",
    "ModelResolutionProof",
    "ModelResolutionRouteHop",
    "ModelRoutePlan",
    "ModelTierAttempt",
    "ModelTieredResolutionResult",
    "ModelTrustDomain",
]
