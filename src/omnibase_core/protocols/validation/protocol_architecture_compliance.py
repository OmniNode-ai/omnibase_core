"""
Protocol definition for architectural compliance checking.

This module provides the ProtocolArchitectureCompliance protocol which
validates dependency compliance and layer separation.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolArchitectureCompliance(Protocol):
    """
    Protocol for architectural compliance checking.

    Validates dependency compliance and layer separation.
    """

    allowed_dependencies: list[str]
    forbidden_dependencies: list[str]
    required_patterns: list[str]
    layer_violations: list[str]

    async def check_dependency_compliance(self, imports: list[str]) -> list[str]:
        """
        Check if imports comply with dependency rules.

        Args:
            imports: List of import statements

        Returns:
            List of violations
        """
        ...

    async def validate_layer_separation(
        self, file_path: str, imports: list[str]
    ) -> list[str]:
        """
        Validate layer separation for a file.

        Args:
            file_path: Path to the file
            imports: List of imports in the file

        Returns:
            List of layer violations
        """
        ...


__all__ = ["ProtocolArchitectureCompliance"]
