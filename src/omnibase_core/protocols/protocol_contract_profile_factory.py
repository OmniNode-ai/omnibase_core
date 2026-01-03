"""
Contract Profile Factory Protocol.

This module provides the ProtocolContractProfileFactory protocol which defines
the interface for factories that create default contract profiles for different
node types. Contract profiles provide pre-configured templates for common node
use cases.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from typing import Protocol, runtime_checkable

from omnibase_core.enums import EnumNodeType
from omnibase_core.models.contracts import ModelContractBase

__all__ = ["ProtocolContractProfileFactory"]


@runtime_checkable
class ProtocolContractProfileFactory(Protocol):
    """
    Protocol for contract profile factories.

    Defines the interface for factories that create default contract profiles
    for different node types. Contract profiles provide pre-configured templates
    for common node use cases, reducing boilerplate when creating new nodes.

    Key Features:
        - Node type-specific profile lookup
        - Version-aware profile generation
        - Discovery of available profiles per node type

    Example:
        .. code-block:: python

            from omnibase_core.protocols import ProtocolContractProfileFactory
            from omnibase_core.enums import EnumNodeType

            def create_node_contract(
                factory: ProtocolContractProfileFactory,
                node_type: EnumNodeType,
            ) -> ModelContractBase:
                '''Create a default contract for a node type.'''
                # Check available profiles
                profiles = factory.available_profiles(node_type)
                if "default" in profiles:
                    return factory.get_profile(node_type, "default")
                return factory.get_profile(node_type, profiles[0])
    """

    def get_profile(
        self,
        node_type: EnumNodeType,
        profile: str,
        version: str = "1.0.0",
    ) -> ModelContractBase:
        """
        Get a default contract profile for a node type.

        Retrieves a pre-configured contract template based on the node type,
        profile name, and optional version. Profiles provide sensible defaults
        for common node configurations.

        Args:
            node_type: The type of node for which to get the profile.
            profile: The name of the profile to retrieve (e.g., "default",
                "minimal", "full").
            version: The semantic version of the profile to retrieve.
                Defaults to "1.0.0".

        Returns:
            A ModelContractBase instance configured according to the
            specified profile.

        Raises:
            KeyError: If the requested profile does not exist for the
                given node type.
            ValueError: If the version string is not a valid semantic
                version.
        """
        ...

    def available_profiles(self, node_type: EnumNodeType) -> list[str]:
        """
        List available profiles for a node type.

        Returns the names of all profiles that can be retrieved for the
        specified node type using get_profile().

        Args:
            node_type: The type of node for which to list available profiles.

        Returns:
            A list of profile names available for the given node type.
            May be empty if no profiles are defined for the node type.
        """
        ...
