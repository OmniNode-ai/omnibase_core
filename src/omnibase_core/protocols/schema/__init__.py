"""
Schema protocols package.

This package provides protocol definitions for schema loading and validation.
These are Core-native equivalents of the SPI schema protocols.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from omnibase_core.protocols.schema.protocol_schema_loader import ProtocolSchemaLoader
from omnibase_core.protocols.schema.protocol_schema_model import ProtocolSchemaModel

__all__ = [
    "ProtocolSchemaLoader",
    "ProtocolSchemaModel",
]
