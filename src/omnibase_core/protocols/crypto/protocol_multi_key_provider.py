# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Protocol for multi-key lookup across trust domains and nodes.

Extends the base ``ProtocolKeyProvider`` concept with domain-level trust
root lookup and node identity key retrieval. This enables the capability
token verifier to retrieve the correct public key for signature
verification based on the issuer domain or subject node.

Design Principle:
    Missing keys always result in verification failure (fail-closed).
    Implementations may source keys from files, databases, Vault, or
    Infisical -- the verifier is decoupled from storage backend.

.. versionadded:: 0.21.0
    Phase 3 of authenticated dependency resolution (OMN-2892).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["ProtocolMultiKeyProvider"]


@runtime_checkable
class ProtocolMultiKeyProvider(Protocol):
    """Protocol for retrieving trust root and node identity keys.

    Provides two key retrieval methods for tiered resolution:

    1. **Domain trust roots** -- the Ed25519 public key that anchors trust
       for all tokens issued by a specific trust domain.
    2. **Node identity keys** -- the Ed25519 public key that identifies
       a specific node for identity proofs.

    Security Model:
        - ``None`` return means "key not found" and MUST be treated as
          verification failure by callers.
        - Implementations MUST NOT return stale or revoked keys.
        - Key rotation is handled by the implementation; callers only
          see the current valid key.
    """

    def get_domain_trust_root(self, domain_id: str) -> bytes | None:
        """Retrieve the trust root public key for a domain.

        Args:
            domain_id: The trust domain identifier
                (e.g., ``org.omninode``, ``fed.partner-a``).

        Returns:
            32-byte Ed25519 public key for the domain trust root,
            or ``None`` if the domain is unknown or its key is revoked.
        """
        ...

    def get_node_identity_key(self, node_id: str) -> bytes | None:
        """Retrieve the identity public key for a node.

        Args:
            node_id: The node identifier.

        Returns:
            32-byte Ed25519 public key for the node,
            or ``None`` if the node is unknown or its key is revoked.
        """
        ...
