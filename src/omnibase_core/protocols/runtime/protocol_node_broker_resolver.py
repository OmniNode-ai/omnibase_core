# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Protocol for the resolver that answers which broker a node is reached on (OMN-22362)."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

BindingT_co = TypeVar("BindingT_co", covariant=True)


@runtime_checkable
class ProtocolNodeBrokerResolver(Protocol[BindingT_co]):
    """Resolves a node's broker from the node's contract overlay.

    Core consumes this and cannot read the lab lane declaration, so the package that can
    registers an implementation under the ``onex.node_broker_resolvers`` entry-point group
    (see ``ModelNodeBrokerBinding.for_node``). The binding type is a parameter, and the
    implementation answers ``ModelNodeBrokerBinding``, because the import-layering ratchet
    freezes new ``protocols`` -> ``models`` edges. An implementation raises
    ``ModelNodeBrokerResolutionError`` naming the overlay path when the overlay is missing,
    declares no ``event_bus``, is malformed, or names a lane that is not usable.
    """

    def resolve_node_broker(self, node_id: str) -> BindingT_co:
        """Return the node's binding."""
        ...


__all__ = ["BindingT_co", "ProtocolNodeBrokerResolver"]
