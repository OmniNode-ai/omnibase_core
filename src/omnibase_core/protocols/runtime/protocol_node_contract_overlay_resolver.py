# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Protocol for the resolver that reads a node's contract overlay (OMN-22469)."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

OverlayT_co = TypeVar("OverlayT_co", covariant=True)


@runtime_checkable
class ProtocolNodeContractOverlayResolver(Protocol[OverlayT_co]):
    """Reads the contract section of a node's contract overlay.

    Core cannot read the workspace layout, so the package that can registers an
    implementation under the ``onex.node_contract_overlay_resolvers`` entry-point group (see
    ``ModelNodeContractOverlay.for_node``). The answer type is a parameter, and the
    implementation answers ``ModelNodeContractOverlay``, because the import-layering ratchet
    freezes new ``protocols`` -> ``models`` edges. An implementation answers an empty contract
    for a node with no overlay and raises ``ModelNodeContractOverlayResolutionError`` naming the
    overlay path when the overlay cannot be read or is malformed.
    """

    def resolve_contract_overlay(self, node_id: str) -> OverlayT_co:
        """Return the node's contract overlay."""
        ...


__all__ = ["OverlayT_co", "ProtocolNodeContractOverlayResolver"]
