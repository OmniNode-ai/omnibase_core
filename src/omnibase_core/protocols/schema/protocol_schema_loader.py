"""
Protocol for ONEX schema loaders.

This module provides the ProtocolSchemaLoader protocol definition for loading
ONEX YAML metadata and JSON schemas. This is a Core-native equivalent of the
SPI schema protocol.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.protocols.schema.protocol_schema_model import ProtocolSchemaModel
from omnibase_core.protocols.types import ProtocolNodeMetadataBlock


@runtime_checkable
class ProtocolSchemaLoader(Protocol):
    """
    Protocol for ONEX schema loaders.

    Provides methods for loading ONEX YAML metadata and JSON schemas.
    All methods use str paths and return strongly-typed models.
    """

    async def load_onex_yaml(self, path: str) -> ProtocolNodeMetadataBlock:
        """
        Load an ONEX YAML metadata file.

        Args:
            path: Path to the ONEX YAML file

        Returns:
            Parsed node metadata block
        """
        ...

    async def load_json_schema(self, path: str) -> ProtocolSchemaModel:
        """
        Load a JSON schema file.

        Args:
            path: Path to the JSON schema file

        Returns:
            Parsed schema model
        """
        ...

    async def load_schema_for_node(
        self, node: ProtocolNodeMetadataBlock
    ) -> ProtocolSchemaModel:
        """
        Load the schema associated with a node.

        Args:
            node: The node metadata block

        Returns:
            The schema model for the node
        """
        ...


__all__ = ["ProtocolSchemaLoader"]
