"""
Core-native schema protocols.

This module provides protocol definitions for schema loading and validation.
These are Core-native equivalents of the SPI schema protocols.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from omnibase_core.protocols.types import ProtocolNodeMetadataBlock

if TYPE_CHECKING:
    pass


# =============================================================================
# Schema Model Protocol
# =============================================================================


@runtime_checkable
class ProtocolSchemaModel(Protocol):
    """
    Protocol for schema models.

    Represents a loaded schema that can validate data and provide
    schema information.
    """

    schema_id: str
    schema_type: str
    version: str
    definition: dict[str, object]

    def validate(self, data: dict[str, object]) -> bool:
        """
        Validate data against this schema.

        Args:
            data: The data to validate

        Returns:
            True if valid, False otherwise
        """
        ...

    def to_dict(self) -> dict[str, object]:
        """
        Convert schema to dictionary representation.

        Returns:
            Dictionary representation of the schema
        """
        ...

    async def get_schema_path(self) -> str:
        """
        Get the path to the schema file.

        Returns:
            The schema file path
        """
        ...


# =============================================================================
# Schema Loader Protocol
# =============================================================================


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


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "ProtocolSchemaModel",
    "ProtocolSchemaLoader",
]
