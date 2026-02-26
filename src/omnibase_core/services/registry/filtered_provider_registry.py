# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Filtered provider registry scoped to a single trust domain.

Wraps a ``ProtocolProviderRegistry`` and restricts provider visibility
to those whose capabilities match the trust domain's allowed capability
glob patterns. Used by ``ServiceTieredResolver`` to scope resolution
to a specific trust boundary at each tier.

.. versionadded:: 0.21.0
    Phase 2 of authenticated dependency resolution (OMN-2891).
"""

from __future__ import annotations

__all__ = ["FilteredProviderRegistry"]

import fnmatch
import logging

from omnibase_core.models.providers.model_provider_descriptor import (
    ModelProviderDescriptor,
)
from omnibase_core.models.routing.model_trust_domain import ModelTrustDomain
from omnibase_core.protocols.resolution.protocol_capability_resolver import (
    ProtocolProviderRegistry,
)

logger = logging.getLogger(__name__)


class FilteredProviderRegistry:
    """Provider registry adapter scoped to a single trust domain.

    Wraps an underlying ``ProtocolProviderRegistry`` and filters results
    from ``get_providers_for_capability()`` to only return providers whose
    capabilities match the trust domain's ``allowed_capabilities`` glob
    patterns.

    If the trust domain has no ``allowed_capabilities`` (empty list),
    all providers are visible (open domain).

    Thread Safety:
        This class is stateless beyond its constructor arguments and
        delegates all queries to the underlying registry. Thread safety
        depends on the underlying registry implementation.

    Args:
        base_registry: The underlying provider registry to wrap.
        trust_domain: The trust domain used to filter providers.

    .. versionadded:: 0.21.0
    """

    def __init__(
        self,
        base_registry: ProtocolProviderRegistry,
        trust_domain: ModelTrustDomain,
    ) -> None:
        self._base_registry = base_registry
        self._trust_domain = trust_domain

    def get_providers_for_capability(
        self, capability: str
    ) -> list[ModelProviderDescriptor]:
        """Get providers for a capability, filtered by trust domain scope.

        First checks whether the requested capability is allowed by the
        trust domain's glob patterns. If not, returns an empty list
        without querying the underlying registry.

        If the trust domain has no allowed_capabilities patterns (empty
        list), the domain is considered open and all providers pass.

        Args:
            capability: The capability identifier to query.

        Returns:
            List of provider descriptors from the underlying registry
            that are within the trust domain's allowed capability scope.
        """
        # If domain has capability restrictions, check them first
        allowed = self._trust_domain.allowed_capabilities
        if allowed and not any(
            fnmatch.fnmatch(capability, pattern) for pattern in allowed
        ):
            logger.debug(
                "Capability '%s' not in allowed patterns for domain '%s'",
                capability,
                self._trust_domain.domain_id,
            )
            return []

        providers = self._base_registry.get_providers_for_capability(capability)

        logger.debug(
            "FilteredProviderRegistry[%s]: %d provider(s) for '%s'",
            self._trust_domain.domain_id,
            len(providers),
            capability,
        )

        return providers

    @property
    def trust_domain(self) -> ModelTrustDomain:
        """The trust domain this registry is scoped to."""
        return self._trust_domain

    def __repr__(self) -> str:
        """Return representation for debugging."""
        return (
            f"FilteredProviderRegistry("
            f"domain={self._trust_domain.domain_id!r}, "
            f"tier={self._trust_domain.tier.value})"
        )
