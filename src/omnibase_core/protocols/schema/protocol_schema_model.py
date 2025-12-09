"""
Protocol for schema models.

This module provides the ProtocolSchemaModel protocol definition for schema
loading and validation. This is a Core-native equivalent of the SPI schema protocol.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class ProtocolSchemaModel(Protocol):
    """
    Protocol for schema models.

    Represents a loaded schema that can validate data and provide
    schema information.
    """

    schema_id: UUID
    schema_type: str
    # error-ok: string_version - Protocol attribute; implementers may use str or ModelSemVer
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


__all__ = ["ProtocolSchemaModel"]
