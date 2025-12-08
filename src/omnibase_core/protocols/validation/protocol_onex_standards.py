"""
Protocol definition for ONEX ecosystem architectural standards and conventions.

This module provides the ProtocolONEXStandards protocol which defines and
validates ONEX naming conventions, directory structure requirements, and
forbidden patterns.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolONEXStandards(Protocol):
    """
    Protocol for ONEX ecosystem architectural standards and conventions.

    Defines and validates ONEX naming conventions, directory structure
    requirements, and forbidden patterns.
    """

    enum_naming_pattern: str
    model_naming_pattern: str
    protocol_naming_pattern: str
    node_naming_pattern: str
    required_directories: list[str]
    forbidden_patterns: list[str]

    async def validate_enum_naming(self, name: str) -> bool:
        """Validate enum naming convention."""
        ...

    async def validate_model_naming(self, name: str) -> bool:
        """Validate model naming convention."""
        ...

    async def validate_protocol_naming(self, name: str) -> bool:
        """Validate protocol naming convention."""
        ...

    async def validate_node_naming(self, name: str) -> bool:
        """Validate node naming convention."""
        ...


__all__ = ["ProtocolONEXStandards"]
