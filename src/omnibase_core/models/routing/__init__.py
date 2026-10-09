# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Routing models for tiered authenticated dependency resolution.

The type system for trust-domain-scoped, tiered
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
    Phase 7 adds ModelTieredResolutionConfig and ModelTrustDomainConfig
    for declarative contract YAML integration (OMN-2896).
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.routing.model_capability_token import ModelCapabilityToken
    from omnibase_core.models.routing.model_ci_override_policy import (
        ModelCiOverridePolicy,
    )
    from omnibase_core.models.routing.model_classification_gate import (
        ModelClassificationGate,
    )
    from omnibase_core.models.routing.model_hop_constraints import ModelHopConstraints
    from omnibase_core.models.routing.model_llm_route_rejected_event import (
        ModelLlmRouteRejectedEvent,
    )
    from omnibase_core.models.routing.model_llm_route_resolved_event import (
        ModelLlmRouteResolvedEvent,
    )
    from omnibase_core.models.routing.model_policy_bundle import ModelPolicyBundle
    from omnibase_core.models.routing.model_redaction_policy import ModelRedactionPolicy
    from omnibase_core.models.routing.model_resolution_event import ModelResolutionEvent
    from omnibase_core.models.routing.model_resolution_proof import ModelResolutionProof
    from omnibase_core.models.routing.model_resolution_route_hop import (
        ModelResolutionRouteHop,
    )
    from omnibase_core.models.routing.model_route_plan import ModelRoutePlan
    from omnibase_core.models.routing.model_routing_decision import (
        EnumCapabilityTier,
        EnumProvider,
        EnumRetryType,
        EnumRiskLevel,
        ModelRoutingDecision,
    )
    from omnibase_core.models.routing.model_routing_degraded_event import (
        ModelRoutingDegradedEvent,
    )
    from omnibase_core.models.routing.model_routing_policy import ModelRoutingPolicy
    from omnibase_core.models.routing.model_served_model_name import (
        ModelServedModelName,
    )
    from omnibase_core.models.routing.model_served_model_ref import ModelServedModelRef
    from omnibase_core.models.routing.model_tier_attempt import ModelTierAttempt
    from omnibase_core.models.routing.model_tiered_resolution_config import (
        ModelTieredResolutionConfig,
    )
    from omnibase_core.models.routing.model_tiered_resolution_result import (
        ModelTieredResolutionResult,
    )
    from omnibase_core.models.routing.model_trust_domain import ModelTrustDomain
    from omnibase_core.models.routing.model_trust_domain_config import (
        ModelTrustDomainConfig,
    )

__all__ = [
    "EnumCapabilityTier",
    "EnumProvider",
    "EnumRetryType",
    "EnumRiskLevel",
    "ModelCapabilityToken",
    "ModelClassificationGate",
    "ModelCiOverridePolicy",
    "ModelHopConstraints",
    "ModelLlmRouteRejectedEvent",
    "ModelLlmRouteResolvedEvent",
    "ModelServedModelRef",
    "ModelServedModelName",
    "ModelPolicyBundle",
    "ModelRedactionPolicy",
    "ModelResolutionEvent",
    "ModelResolutionProof",
    "ModelResolutionRouteHop",
    "ModelRoutePlan",
    "ModelRoutingDecision",
    "ModelRoutingDegradedEvent",
    "ModelRoutingPolicy",
    "ModelTierAttempt",
    "ModelTieredResolutionConfig",
    "ModelTieredResolutionResult",
    "ModelTrustDomain",
    "ModelTrustDomainConfig",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelCapabilityToken": (
        "omnibase_core.models.routing.model_capability_token",
        "ModelCapabilityToken",
    ),
    "ModelCiOverridePolicy": (
        "omnibase_core.models.routing.model_ci_override_policy",
        "ModelCiOverridePolicy",
    ),
    "ModelClassificationGate": (
        "omnibase_core.models.routing.model_classification_gate",
        "ModelClassificationGate",
    ),
    "ModelHopConstraints": (
        "omnibase_core.models.routing.model_hop_constraints",
        "ModelHopConstraints",
    ),
    "ModelLlmRouteRejectedEvent": (
        "omnibase_core.models.routing.model_llm_route_rejected_event",
        "ModelLlmRouteRejectedEvent",
    ),
    "ModelLlmRouteResolvedEvent": (
        "omnibase_core.models.routing.model_llm_route_resolved_event",
        "ModelLlmRouteResolvedEvent",
    ),
    "ModelPolicyBundle": (
        "omnibase_core.models.routing.model_policy_bundle",
        "ModelPolicyBundle",
    ),
    "ModelRedactionPolicy": (
        "omnibase_core.models.routing.model_redaction_policy",
        "ModelRedactionPolicy",
    ),
    "ModelResolutionEvent": (
        "omnibase_core.models.routing.model_resolution_event",
        "ModelResolutionEvent",
    ),
    "ModelResolutionProof": (
        "omnibase_core.models.routing.model_resolution_proof",
        "ModelResolutionProof",
    ),
    "ModelResolutionRouteHop": (
        "omnibase_core.models.routing.model_resolution_route_hop",
        "ModelResolutionRouteHop",
    ),
    "ModelRoutePlan": (
        "omnibase_core.models.routing.model_route_plan",
        "ModelRoutePlan",
    ),
    "EnumCapabilityTier": (
        "omnibase_core.models.routing.model_routing_decision",
        "EnumCapabilityTier",
    ),
    "EnumProvider": (
        "omnibase_core.models.routing.model_routing_decision",
        "EnumProvider",
    ),
    "EnumRetryType": (
        "omnibase_core.models.routing.model_routing_decision",
        "EnumRetryType",
    ),
    "EnumRiskLevel": (
        "omnibase_core.models.routing.model_routing_decision",
        "EnumRiskLevel",
    ),
    "ModelRoutingDecision": (
        "omnibase_core.models.routing.model_routing_decision",
        "ModelRoutingDecision",
    ),
    "ModelRoutingDegradedEvent": (
        "omnibase_core.models.routing.model_routing_degraded_event",
        "ModelRoutingDegradedEvent",
    ),
    "ModelRoutingPolicy": (
        "omnibase_core.models.routing.model_routing_policy",
        "ModelRoutingPolicy",
    ),
    "ModelServedModelName": (
        "omnibase_core.models.routing.model_served_model_name",
        "ModelServedModelName",
    ),
    "ModelServedModelRef": (
        "omnibase_core.models.routing.model_served_model_ref",
        "ModelServedModelRef",
    ),
    "ModelTierAttempt": (
        "omnibase_core.models.routing.model_tier_attempt",
        "ModelTierAttempt",
    ),
    "ModelTieredResolutionConfig": (
        "omnibase_core.models.routing.model_tiered_resolution_config",
        "ModelTieredResolutionConfig",
    ),
    "ModelTieredResolutionResult": (
        "omnibase_core.models.routing.model_tiered_resolution_result",
        "ModelTieredResolutionResult",
    ),
    "ModelTrustDomain": (
        "omnibase_core.models.routing.model_trust_domain",
        "ModelTrustDomain",
    ),
    "ModelTrustDomainConfig": (
        "omnibase_core.models.routing.model_trust_domain_config",
        "ModelTrustDomainConfig",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
