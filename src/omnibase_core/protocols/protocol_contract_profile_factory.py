"""
Contract Profile Factory Protocol.

Defines the protocol interface for contract profile factories.
"""

from typing import Protocol, runtime_checkable

from omnibase_core.enums import EnumNodeType
from omnibase_core.models.contracts import ModelContractBase

__all__ = ["ProtocolContractProfileFactory"]


@runtime_checkable
class ProtocolContractProfileFactory(Protocol):
    """
    Protocol interface for contract profile factories.

    Defines the interface that factory implementations must follow.
    """

    def get_profile(
        self,
        node_type: EnumNodeType,
        profile: str,
        version: str = "1.0.0",
    ) -> ModelContractBase:
        """Get a default contract profile."""
        ...

    def available_profiles(self, node_type: EnumNodeType) -> list[str]:
        """List available profiles for a node type."""
        ...
