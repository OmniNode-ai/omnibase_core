"""
ProtocolCapabilityProvider - Protocol for capability providers.

This module provides the protocol definition for objects that provide
node capabilities and contract-derived capabilities for auto-discovery.

OMN-1124: Protocol for capability-based auto-discovery and registration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.capabilities.model_contract_capabilities import (
        ModelContractCapabilities,
    )


@runtime_checkable
class ProtocolCapabilityProvider(Protocol):
    """
    Protocol for objects that provide capability information.

    This protocol defines the interface for nodes and services that
    expose their capabilities for auto-discovery and registration.
    It enables capability-based routing and service matching.

    Methods:
        get_capabilities: Return node capabilities dictionary.
        get_contract_capabilities: Return contract-derived capabilities or None.

    Use Cases:
        - Service discovery: Find nodes with specific capabilities
        - Intent routing: Route intents to capable handlers
        - Protocol validation: Verify nodes implement required protocols
        - Auto-registration: Register nodes based on declared capabilities

    Example:
        class MyNode:
            def get_capabilities(self) -> dict[str, object]:
                return {
                    "node_type": "COMPUTE",
                    "supports_caching": True,
                    "max_parallelism": 4,
                }

            def get_contract_capabilities(self) -> ModelContractCapabilities | None:
                from omnibase_core.models.primitives.model_semver import ModelSemVer
                return ModelContractCapabilities(
                    contract_type="compute",
                    contract_version=ModelSemVer(major=1, minor=0, patch=0),
                    intent_types=["ProcessData"],
                    protocols=["ProtocolCompute"],
                    capability_tags=["pure", "cacheable"],
                )

        node: ProtocolCapabilityProvider = MyNode()  # Type-safe!
    """

    def get_capabilities(self) -> dict[str, object]:
        """
        Get the node's capabilities dictionary.

        Returns general capabilities information about the node,
        including its type, supported features, and operational limits.

        Returns:
            Dictionary containing capability information. The structure
            is flexible to accommodate various node types and use cases.

        Example:
            {
                "node_type": "EFFECT",
                "supports_retry": True,
                "max_retries": 3,
                "timeout_seconds": 30,
            }
        """
        ...

    def get_contract_capabilities(self) -> ModelContractCapabilities | None:
        """
        Get contract-derived capabilities for auto-discovery.

        Returns structured capabilities derived from the node's contract,
        enabling capability-based routing and service registration.
        Returns None if the node has no contract-based capabilities.

        Returns:
            ModelContractCapabilities instance with contract metadata,
            or None if no contract capabilities are available.

        Note:
            The return type uses forward reference to avoid circular
            imports between the protocols and models packages.
        """
        ...


__all__ = ["ProtocolCapabilityProvider"]
