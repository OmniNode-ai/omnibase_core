"""
Capabilities protocols for ONEX nodes.

This package provides protocol definitions for capability providers
to enable capability-based auto-discovery and registration.

Modules:
    protocol_capability_provider: Protocol for capability providers.

Usage:
    from omnibase_core.protocols.capabilities import ProtocolCapabilityProvider

    class MyNode:
        def get_capabilities(self) -> dict[str, Any]:
            return {"node_type": "COMPUTE"}

        def get_contract_capabilities(self) -> ModelContractCapabilities | None:
            return ModelContractCapabilities(...)

    # Type-safe duck typing check
    node: ProtocolCapabilityProvider = MyNode()

OMN-1124: Capabilities protocols package.
"""

from omnibase_core.protocols.capabilities.protocol_capability_provider import (
    ProtocolCapabilityProvider,
)

__all__ = [
    "ProtocolCapabilityProvider",
]
